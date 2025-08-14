
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
You will receive a JSON block with:
• "ingredients": flat list of ingredient strings
• "nutrition": object with nutrient → value pairs

JSON INPUT
----------
{cleaned_ocr}

TOOLS
-----
1. get_aliases(name:str, top:int=20)
2. get_e_number_info(code:str)
3. get_research_papers(query:str)
4. get_warnings(query:str)

For every ingredient name (and any detected E-number), attempt all tools, even E-number ingredients, use all tools on
these E-numbers as well, including the tools get_e_number_info, get_aliases,get_research, get_warnings.
use each tool on each ingredient name and E-number once, don't recall the same tool on the same ingredient name or E-number.
 If a tool yields nothing, return empty results. Do not fabricate data.
Output a Python-serializable dict keyed by ingredient name containing these tool outputs.
"""


def formatter_prompt(schema_str, agent_out, cleaned_ocr) -> str:
    return textwrap.dedent(f"""
You are a food label extraction assistant. Produce ONE valid JSON object that matches the given SCHEMA exactly. Use only values found in the inputs; if missing, use the specified defaults.

INPUTS
------
1) agent_out: a dict keyed by ingredient name. Each value may include results from tools:
   - get_aliases: [alias, ...]
   - get_research_papers: [(title, doi_url_or_doi), ...]
   - get_warnings: {{ "warnings": [str], "confidence scores": [num], "related papers": [str] }}
   - get_e_number_info: {{ "EXXX": {{ "name": str, "purpose": str, "status": str }} }}
2) cleaned_ocr: JSON extracted from OCR (serving size/info, macro nutrients, etc.)
3) schema_str: a string representation of the SCHEMA to match.
INPUTS
------
AGENT_OUT
---------
{agent_out}

CLEANED_OCR
-----------
{cleaned_ocr}

SCHEMA
------
{schema_str}


HARD RULES
----------
1) Output MUST be one JSON object matching the SCHEMA keys, nesting, and order exactly. No markdown, no prose, no comments, no extra keys, no emojis.
2) Types:
   - Strings: use "" if missing.
   - Numbers: use 0.0 if missing.
   - Strings: use "true"/"false" (quoted, NOT BOOL).
   - Arrays: [] if empty.
   - Objects: include all required keys with defaults if missing.
3) Place units ONLY in `micronutrients[i].unit`. All values in `nutritional_facts` are plain numbers (per serving). Do NOT append unit strings there.
4) `ingredients[*].banned` MUST be boolean. If no banned info is present, set false. If any source explicitly states banned, set true.
5) `ingredients[*].research_papers` MUST be a list of objects with keys `"title"` and `"doi"`. If the second element of a tuple is a URL, convert to a DOI string if present in the URL (strip prefixes like "https://doi.org/"); otherwise keep the URL string as the doi value.
6) Deduplicate all lists (`other_names`, warnings, allergens, research papers by (title, doi)).
7) Normalize obvious E-number aliases in ingredients if present (e.g., prefer "E951" to "Aspartame" when OCR shows both; keep both by listing the other in `other_names`).
8) No trailing commas. Must pass `json.loads()`.
9) Never use Non-breaking hyphens (U+2011) or U+2014 (em dash) or any other non-standard characters in the output, always use standard hyphens (U+002D).
10) Always use smaall letters for everything except for the paper tiles and doi, which should be in the same case as the input.

MAPPING AND PRIORITY
--------------------
1) When a field exists in both agent_out and cleaned_ocr, prefer agent_out for (aliases, papers, warnings), and cleaned_ocr for (serving and numeric nutrient values).
2) Serve per-serving values:
   - nutritional_facts.calories, protein, carbohydrate.total, carbohydrate.dietary_fiber, carbohydrate.total_sugars, carbohydrate.added_sugars, fat.total, fat.saturated_fat, fat.trans_fat
   - If units are provided in OCR, parse the numeric and drop the unit (store units only in micronutrients list).
3) Micronutrients: produce a list of objects [{{ "name": str, "value": float, "unit": str }}]
   Examples: cholesterol (mg), sodium (mg), vitamin d (µg), calcium (mg), iron (mg), potassium (mg), magnesium (mg), zinc (mg). If missing, leave the list empty.

INGREDIENT ENRICHMENT
---------------------
For each ingredient:
- name: from key in agent_out or OCR.
- description: brief 1-2 sentence summary (what it is, purpose, source).
- category: use source category if present, else classify into one of:
  ["Sweetener","Dairy","Grain","Protein","Protein Supplement","Fat","Oil","Emulsifier","Preservative","Coloring","Flavoring","Acidifier","Stabilizer","Thickener","Antioxidant","Leavening","Humectant","Fortificant","Spice","Herb","Legume","Nut","Fruit","Vegetable","Cereal","Seaweed","Additive","Seasoning"]
- other_names: use get_aliases and obvious synonyms, deduped.
- safety.warnings: short strings from get_warnings.warnings (if any).
- safety.allergens: standard allergens if applicable (e.g., ["Milk","Soy","Egg","Peanut","Tree Nuts","Fish","Crustacean","Wheat","Gluten","Sesame","Mustard","Celery","Lupin","Sulphites"]).
- banned: per HARD RULES #4.
- research_papers: per HARD RULES #5.
- Note: Purpose (Catagory) of Salt is Seasoning/Perservative

NOTES CONSTRUCTION
------------------
Compute per serving from the numeric fields. Use these thresholds:
- sugar = nutritional_facts.carbohydrate.total_sugars (g)
  • ≥15 → "High in Sugar" ; ≤2.5 → "Low Sugar"
- fat = nutritional_facts.fat.total (g)
  • ≥15.6 → "High in Fat" ; ≤3 → "Low Fat"
- sat_fat = nutritional_facts.fat.saturated_fat (g)
  • ≥4 → "High in Saturated Fat"
- trans_fat = nutritional_facts.fat.trans_fat (g)
  • >0 → "Contains Trans-Fat"
- fibre = nutritional_facts.carbohydrate.dietary_fiber (g)
  • ≥6 → "High in Fibre" ; ≤1.4 → "Low Fibre"
- protein = nutritional_facts.protein (g)
  • ≥10 → "High in Protein"
- cholesterol (mg) and sodium (mg) from micronutrients list:
  • cholesterol ≥60 → "High Cholesterol"
  • sodium ≥460 → "High in Sodium" ; ≤115 → "Low Sodium"
- Vitamins/minerals from micronutrients (use their units):
  • vit d ≥4 µg → "High in Vitamin D"
  • calcium ≥260 mg → "High in Calcium"
  • iron ≥3.6 mg → "High in Iron"
  • potassium ≥940 mg → "High in Potassium"
  • magnesium ≥84 mg → "High in Magnesium"
  • zinc ≥3 mg → "High in Zinc"

Ingredient-based flags (dedupe; one allergen note per type):
- If any ingredient has category "Sweetener" and is artificial (not natural) → add "Contains Artificial Sweetener (INGREDIENT_NAME)" to negative.
- If any ingredient has category "Coloring" and is artificial → add "Contains Artificial Color (INGREDIENT_NAME)" to neutral.
- If any ingredient has category "Preservative" → add "Contains Preservative (INGREDIENT_NAME)" to neutral.
- If any ingredient is banned in any region (Region is given) → add "Contains Banned Ingredient (NAME) in (REGION)" to critical.
- Allergen notes: "Contains Allergen (X)" for any present allergen (Milk, Eggs, Fish, Shellfish/Crustacean, Peanuts, Tree Nuts, Wheat, Gluten, Soy, Sesame, Mustard, Celery, Lupin, Sulphites).
- E-number allergen hints:
  • E322 → Soy
  • E1105 → Egg
  • E441 → Fish/Pork/Beef (gelatin) — pick the explicit source if provided
  • E120 → insect/shellfish cross-reactivity
  • E160d → Annatto (rare anaphylaxis)
  • E407a → seaweed/seafood cross-reactivity
  • E621–E635 → MSG intolerance

OUTPUT
------
Return ONLY the final JSON object. No extra text.
Use the SCHEMA key order. Ensure it parses with json.loads().
""")

