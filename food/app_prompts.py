
import textwrap
x = "Test"
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


def formatter_prompt(schema_str, agent_out, cleaned_ocr) -> str:
    return textwrap.dedent(f"""
        You are a food-label extraction assistant.
        Return ONLY a JSON object matching the schema below. Include every key, even if empty or zero.
        Add any extra nutrition fields present, but always keep the four base keys.
        {schema_str}

        RULES:
        1. Use double quotes for all keys/strings; booleans in lowercase.
        2. Keep key order as in schema.
        3. For missing values: use "" (string), 0.0 (number), false (boolean), [] (list).
        4. “research_papers”: list of {{title, doi}} (empty if none).
        5. “safety.warnings”: list of {{warning, region}} (empty if none).
        6. Add a brief description for each ingredient if missing.
        7. No comments, markdown, single quotes, back-ticks, or trailing commas.
        8. If serving_size missing: "", if serving_per_container missing: 0.0.
        9. If micronutrients missing: [] (empty list).
        10. Output must be valid JSON (parse with json.loads()).

        NOTES:
        - "notes" is a dict with 4 keys: "positive", "neutral", "negative", "critical".
        - Each is a list of unique flags, in this order: positive, neutral, negative, critical.
        - Example:
          "notes": {{
            "positive": ["Low Sugar", "High in Protein"],
            "neutral": ["Contains Preservative"],
            "negative": ["High in Sugar", "Contains Allergen (Milk)"],
            "critical": ["Contains Banned Ingredient (Potassium Bromate) – Banned in EU, UK, Canada, China, India – Reason: Carcinogenic in animal studies ⚫️"]
          }}

        - Assess nutrition per serving using WHO/EFSA thresholds:
          sugar ≥15g → High in Sugar; ≤2.5g → Low Sugar
          fat ≥15.6g → High in Fat; ≤3g → Low Fat
          sat_fat ≥4g → High in Saturated Fat
          trans_fat >0g → Contains Trans-Fat
          cholesterol ≥60mg → High Cholesterol
          sodium ≥460mg → High in Sodium; ≤115mg → Low Sodium
          fibre ≥6g → High in Fibre; ≤1.4g → Low Fibre
          protein ≥10g → High in Protein
          vit_d ≥4µg → High in Vitamin D
          calcium ≥260mg → High in Calcium
          iron ≥3.6mg → High in Iron
          potassium ≥940mg → High in Potassium
          magnesium ≥84mg → High in Magnesium
          zinc ≥3mg → High in Zinc

        - Scan ingredients for flags:
          • Artificial sweetener → negative
          • Artificial color → neutral
          • Preservative → neutral
          • Banned ingredient → critical
          • Common allergens (milk, egg, fish, shellfish, peanuts, tree nuts, wheat/gluten, soy, sesame, celery) or derivatives → negative ("Contains Allergen (X)")
          • E-number allergens: E322 (soy), E1105 (egg), E441 (fish/pork/beef), E120 (insect/shellfish), E160d (anaphylaxis), E407a (seafood), E621–E635 (MSG)
          • One allergen note per type.

        - No duplicates in any list.

        IMPORTANT:
        - Output must match the schema exactly.
        - notes must have 4 keys: "positive", "neutral", "negative", "critical"
        - Return valid JSON ONLY—no markdown, comments, or prose.
        - Every key and string in double quotes.
        - Must pass json.loads().
        - Include all info from agent output and cleaned OCR (ingredients and nutrition/micronutrients).

        Messy text and OCR output:
        \"\"\"Output of the agent (with information about ingredients): {agent_out}, ingredients and nutritions alone: {cleaned_ocr}\"\"\"
    """)

