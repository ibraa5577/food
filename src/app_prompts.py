
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


def formatter_prompt(schema_str, agent_out, cleaned_ocr) -> str:
    return textwrap.dedent(f"""
You are a food label extraction assistant. Your task is to produce a single valid JSON object, matching the following schema exactly, using information from the agent output and the cleaned OCR. Only include values present in the sources; use default values for missing keys as specified.

SCHEMA:
{schema_str}

STRICT EXTRACTION AND OUTPUT RULES:
1. Output must be a single JSON object matching the schema above exactly. Do not add, remove, or reorder keys.
2. All keys must be present, in the order shown in the schema, even if empty or zero.
3. Use only double quotes for all keys and strings. All booleans must be lowercase (true/false) inside double qoutation marks. No trailing commas.
4. For missing or unavailable data:
   - Use "" (empty string) for string fields.
   - Use 0.0 for numeric fields.
   - Use false for boolean fields.
   - Use [] (empty list) for array fields.
   - For objects or nested dicts, include all keys with appropriate default values.
5. Do not include any instructional text, placeholders, or comments. Output only valid JSON.
6. For ingredient lists, output each ingredient as an object with its required fields. If a field is missing, use its default.
7. For "research_papers", always output a list of objects with "title" and "doi" keys, or an empty list if none.
8. For "safety.warnings", always output a list of objects with "warning" or an empty list if none.
9. For "notes", always output a dictionary with exactly these keys, in order: "positive", "neutral", "negative", "critical". Each must be a list (empty if no values).
10. For "serving_info", if "serving_size" is not found, set to "". If "serving_per_container" is not found, set to 0.0.
11. For "micronutrients", if not found, output an empty list [].
12. All numeric values must be strings with units (e.g., "10 g", "100 mg", "50 kcal") if units are present in the source; otherwise, output as "0.0".
13. Map all extracted fields to the schema's key names. If a value is present in either agent_out or cleaned_ocr, use it. If present in both, prefer agent_out.
14. Never output any extraneous symbols, markdown, or prose.

PROCESS:
1. Parse both agent_out and cleaned_ocr for all possible values for each schema key.
2. For every field in the schema, use the value from agent_out if present, otherwise use cleaned_ocr, otherwise use the specified default.
3. For lists of objects (such as ingredients), ensure each object contains all required keys with appropriate values or defaults.
4. For nested objects, include all required keys even if empty or zero.
5. Output only the final JSON object, valid and parseable by json.loads().


Few-shot examples:
Example 1:
agent_out = 
INPUT DATA:
Output of the agent: {agent_out}
Cleaned OCR: {cleaned_ocr}
""")

