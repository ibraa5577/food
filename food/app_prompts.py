
import textwrap

def cleaning_prompt(ocr_text: str) -> str:
    return f"""
You are a data extraction assistant. Extract ONLY the English content from the given OCR food label.

### Instructions:
1. Extract "ingredients" → List of ingredients, remove extra descriptions like color or perservative, only extract ingredients, if it has an E-number, USE IT INSTEAD.
2. Extract "nutrition" → Key-value pairs for common nutrition facts (energy, fat, protein, carbohydrates, sugars, fiber, etc.).
3. If a field is missing, omit it.
4. Expect mistakes, misspells, etc... and you will fix them.

### STRICT OUTPUT RULES:
- Return **ONLY valid JSON**. No markdown, no extra characters.
- If OCR text doesn't contain a specifc ingredient/nutrition, omit it, don't add it, if it
contains more ingredients/nutrition, add them.
- DON'T SKIP ANY INGREDIENT OR NUTRITION, ADD THEM!!!!!
- No non-English characters.
- Use this structure EXACTLY:
{{
  "ingredients": ["Ingredient", "Ingredient"],
  "serving_info": {{
    "serving_size": "value",
    "serving_per_container": 0.0
  }},
  "nutrition": {{
  "nutrition": {{
    "energy_kcal": "value",
    "fat": "value",
    "trans_fat": "value",
    "saturated_fat": "value",
    "omega_3": "value",
    "omega_6": "value",
    "cholesterol": "value",
    "carbohydrates": "value",
    "sugar": "value",
    "added_sugar": "value",
    "fiber": "value",
    "protein": "value",
    "sodium": "value",
    "alcohol": "value",
  }},
  "micronutrients": {{
    "vitamin_a": "value",
    "vitamin_c": "value",
    "vitamin_d": "value",
    "vitamin_e": "value",
    "vitamin_k": "value",
    "vitamin_b1": "value",
    "vitamin_b2": "value",
    "vitamin_b3": "value",
    "vitamin_b5": "value",
    "vitamin_b6": "value",
    "vitamin_b7": "value",
    "vitamin_b9": "value",
    "vitamin_b12": "value",
    "calcium": "value",
    "iron": "value",
    "potassium": "value",
    "magnesium": "value",
    "zinc": "value",
    "phosphorus": "value",
    "manganese": "value",
    "copper": "value",
    "selenium": "value",
    "chromium": "value",
    "iodine": "value",
    "fluoride": "value",
    "molybdenum": "value"
  }}
}}
if serving_size is not given, give it an empty string like this "", if serving_per_container is not given,
give a value of 0.0, if any nutrition is not given, give it a value of 0.0, if nutrition is not given, give it an empty list like this []
all nutrition values you should add to them the units, like "g", "mg", "µg", "kcal", etc.
\"\"\"{ocr_text}\"\"\"
"""


def agent_prompt(cleaned_ocr: str) -> str:
    return f"""
You will receive a JSON block with two keys:

• "ingredients": a flat list of ingredient strings
• "nutrition":   an object with nutrient → value pairs

JSON INPUT
----------
{cleaned_ocr}
If no ingredient provided, output the nutritional facts as json (big Key is "nutrition", another dictionary
containing them, and their values are their amount)


TOOL CATALOG
-------------
1. get_aliases(name:str, top:int=20)
2. get_e_number_info(code:str)
3. get_research_papers(query:str)
4. get_warnings(query:str
use them all for every single ingredient
"""


def formatter_prompt(schema_str,agent_out,cleaned_ocr) -> str:
    return textwrap.dedent(f"""
        You are a food-label extraction assistant.
        Return ONLY a JSON object matching the schema below – include **every** key even if empty/zero.
        add nutritions if not available in the schema below.
        {schema_str}

        EXTRACTION RULES
        1.  Use double quotes; booleans in lowercase.
        2.  Keep key order exactly as in schema.
        3.  Missing values → "" (string), 0.0 (number), false (boolean), [] (list).
        4.  Accept extra nutrition fields (sugar, sodium, fibre, etc.) if present, but always keep the four base keys.
        5.  “research_papers” → list of {{title, doi}} objects (empty list if none).
        6.  “safety.warnings” → list of {{warning, region}} objects (empty list if none).
        7.  Add descriptions to ingredients, if not given. a brief description about what it is and its main source
        8.  Return ONLY valid JSON.
        9.  Every key and string must be wrapped in double quotes (").
        10. No back-ticks, no comments, no single quotes, no trailing commas.
        11. If serving_size is not given, give it an empty string like this "", if serving_per_container is not given,
            give a value of 0.0
        12. if micronutrients is not given, give it an empty list like this [] EMPTY LIST IF NO MICRONUTRIENTS

      NOTES CONSTRUCTION
      • Return “notes” as a dictionary with 4 keys:
          – "positive": list of **positive** flags (e.g., Low Sugar, High in Protein)
          – "neutral": list of **neutral**/cautionary flags (e.g., Contains Preservative)
          – "negative": list of **negative**/health risk flags (e.g., Contains Allergen)
          – "critical": list of **critical** flags (e.g., Contains Banned Ingredient, proven cancerious ingredient.)

      • Evaluate nutritional_facts **per serving** against WHO/EFSA guidelines:
          – sugar ≥15 g       →  High in Sugar
          – sugar ≤2.5 g      →  Low Sugar
          – fat ≥15.6 g       →  High in Fat
          – fat ≤3 g          →  Low Fat
          – sat_fat ≥4 g      →  High in Saturated Fat
          – trans_fat >0 g    →  Contains Trans-Fat
          – cholesterol ≥60 mg →  High Cholesterol
          – sodium ≥460 mg    →  High in Sodium
          – sodium ≤115 mg    →  Low Sodium
          – fibre ≥6 g        →  High in Fibre
          – fibre ≤1.4 g      →  Low Fibre
          – protein ≥10 g     →  High in Protein
          – vit_d ≥4 µg       →  High in Vitamin D
          – calcium ≥260 mg   →  High in Calcium
          – iron ≥3.6 mg      →  High in Iron
          – potassium ≥940 mg →  High in Potassium
          – magnesium ≥84 mg  →  High in Magnesium
          – zinc ≥3 mg        →  High in Zinc

      •  Scan ingredients and add flags:
          – category contains “Sweetener” and not natural →  negative - Contains Artificial Sweetener
          – category contains “Coloring” and is artificial →  neutral - Contains Artificial Color
          – category contains “Preservative”               →  neutral - Contains Preservative
          – any ingredient banned=true                     → critical -  Contains Banned Ingredient
          – any common allergen (milk, eggs, fish, shellfish, peanuts, tree nuts, wheat/gluten, soy, sesame, celery) → 🔴 Contains Allergen (X)
          – scan for hidden/derivative forms (e.g., caseinate → milk, albumin → egg, maltodextrin-wheat → gluten) → same flag
          – E-number allergens:
                • E322 (soy lecithin)            → soy
                • E1105 (lysozyme)               → egg
                • E441 (gelatin)                 → fish / pork / beef source
                • E120 (carmine)                 → insect / shellfish cross-reactivity
                • E160d (annatto)                → rare anaphylaxis
                • E407a (processed Eucheuma)     → seaweed / seafood cross-reactivity
                • E621–E635 (glutamates)         → MSG intolerance
          – output one allergen note per type: Contains Allergen (X)

      •  No duplicates in any list.
      •  Keep the order: positive, neutral, negative, critical (return empty lists if no notes).
      •  Example:
        "notes": {{
  "positive": [
    "Low Sugar",
    "Low Fat",
    "Low Sodium",
    "High in Fibre",
    "High in Protein",
    "High in Vitamin D",
    "High in Calcium",
    "High in Iron",
    "High in Potassium",
    "High in Magnesium",
    "High in Zinc"
  ],
  "neutral": [
    "Contains Preservative",
    "Contains Natural Color",
    "Contains Natural Sweetener",
    "Contains Acidifier",
    "Contains Emulsifier"
  ],
  "negative": [
    "High in Sugar",
    "High in Fat",
    "High in Saturated Fat",
    "Contains Trans-Fat",
    "High in Sodium",
    "Low Fibre",
    "Contains Artificial Sweetener",
    "Contains Artificial Color",
    "Contains Allergen (Milk)",
    "Contains Allergen (Soy)",
    "Contains Allergen (Shellfish)"
    "Contains Allergen (Egg)",
    "Contains Allergen (Peanut)",
    "Contains Allergen (Tree Nuts)",
    "Contains Allergen (Fish)",
    "Contains Allergen (Crustacean)",
    "Contains Allergen (Wheat)",
    "Contains Allergen (Gluten)",
    "Contains Allergen (Sesame)",
    "Contains Allergen (Mustard)",
    "Contains Allergen (Celery)",
    "Contains Allergen (Lupin)",
    "Contains Allergen (Sulphites)"
  ],
"critical": [
  "Contains Banned Ingredient (Potassium Bromate) – Banned in EU, UK, Canada, China, India – Reason: Carcinogenic in animal studies ⚫️",
  "Contains Banned Ingredient (Rhodamine B) – Banned globally – Reason: Toxic industrial dye used illegally in foods ⚫️",
  "Contains Banned Ingredient (E123 – Amaranth) – Banned in USA – Reason: Linked to cancer and tumors in rats ⚫️",
  "Contains Banned Ingredient (Sudan Dye) – Banned globally – Reason: Carcinogenic synthetic dye not approved for food ⚫️",
  "Severe Allergen Risk (Annatto – E160d) – flagged in USA/Australia – Reason: Reported cases of anaphylaxis ⚫️"
]

}}

      IMPORTANT
      – Output must match the schema exactly.
      – notes must be a dictionary with 4 keys: "positive", "neutral", "negative", "critical"
      – Return valid JSON ONLY. No markdown, comments, or prose.
      – Every key and string must be in double quotes.
      – Must pass json.loads() without error.
        Include all info from the agent output, and the cleaned OCR text (if available) in the output,
        both ingredients and nutrition (and micro) facts.


        Messy text and OCR output:
        \"\"\"Output of the agent (with information about ingredients ): {agent_out}, ingredinets
         and nutritions alone: {cleaned_ocr}\"\"\"
    """)

