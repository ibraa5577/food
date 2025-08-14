from google import genai
from google.genai import types
import requests
import os
import google.generativeai as gemini
import json
import urllib.parse  
import re, requests, pandas as pd
from io import StringIO
import pandas as pd 
import app_config
import agent_tools
import app_prompts
import helper_funcs
import tool_schemas
from typing import Text
import textwrap
from dotenv import load_dotenv
import time


# -------------------------------------Configurations-------------------------------------
start = time.time()
print("Starting the process...")
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_KEY")


# GEMINI_API_KEY = api_key.GEMINI_KEY
models = app_config.models

relevant_keywords = agent_tools.relevant_keywords

aliases_schema = tool_schemas.aliases_schema
e_number_schema = tool_schemas.e_number_schema
research_papers_schema = tool_schemas.research_papers_schema
warnings_schema = tool_schemas.warnings_schema

formatter_schema = app_config.FORMATTER_SCHEMA

warnings_path = app_config.warnings_path
e_numbers_path = app_config.e_numbers_path
warning_df = pd.read_csv(warnings_path).set_index("ingredient")
warning_df.index = warning_df.index.astype(str).str.strip().str.lower()

# -------------------------------------OCR Output-------------------------------------
OCR_file = "ocr_text.txt"

OCR_text = """
NNUTRITION FACTS
Serving Size: 30g
Servings Per Container: about 10
Calories 150
Total Fat 8g
Saturated Fat 3g
Trans Fat 6g
Cholesterol 16mg
Sodium 120mg
Total Carbohydrate 18g
Dietary Fiber 2g
Sugars 16g
Protein 19g
Vitamin D 3mcg
Calcium 50mg
Iron 1.2mg
Potassium 180mg

INGREDIENTS:
Whole Grain Oats, Sugar, MSG, Palm Oil, Cocoa Powder (processed with Alkali), Whey Protein Concentrate, Skim Milk, Soy Lecithin, Salt, Natural Flavors, Artificial Flavors, BHT (for freshness), Milk, Soy.
E951

"""


# -------------------------------------Cleaning Model-------------------------------------
gemini.configure(api_key=GEMINI_API_KEY)
model = gemini.GenerativeModel(models['CLEANING_MODEL'])


def extract_ingredients_and_nutrition(ocr_text: str) -> dict:
  prompt = app_prompts.cleaning_prompt(ocr_text)
  response = model.generate_content(prompt)
  text = response.text.strip()

#Remove code fences and non-ascii characters
  text = re.sub(r"[^\x00-\x7F]+", "", text)
  if text.startswith("```json"):
    text = text.replace("```json", "").replace("```", "").strip()

  try:
    return json.loads(text)
  except json.JSONDecodeError:
    fix_prompt = f"Fix this to be valid JSON only, no explanations:\n{text}"
    fixed = model.generate_content(fix_prompt).text.strip()
    fixed = re.sub(r"[^\x00-\x7F]+", "", fixed)
    try:
      return json.loads(fixed)
    except:
      return {"error": "Invalid JSON", "raw": fixed}

cleaned_ocr = extract_ingredients_and_nutrition(OCR_text)
#print(json.dumps(cleaned_ocr, indent=2))


# -------------------------------------Agentic Model-------------------------------------
client = genai.Client(api_key=GEMINI_API_KEY)

schemas = tool_schemas.schema_list
schemas = types.Tool(function_declarations=schemas)
config = types.GenerateContentConfig(tools=[schemas],
                                     temperature=0,
                                     seed=42)

agent_prompt = app_prompts.agent_prompt(cleaned_ocr)
if cleaned_ocr.get('ingredients'):
  response = client.models.generate_content(
      model='gemini-1.5-flash',
      contents=agent_prompt,
      config=config,
  )
  parts = response.candidates[0].content.parts

  func_map = {
    "get_aliases": agent_tools.aliases,
    "get_e_number_info": agent_tools.e_number_info,
    "get_research_papers": agent_tools.research_papers,
    "get_warnings": agent_tools.warnings
  }
  all_data = {}
  for part in parts:
    call = getattr(part, "function_call", None)
    if call:
      name, args = call.name, call.args
      #print(f"\nCalling: {name} with args {args}")
      if name in func_map:
        result = func_map[name](**args)
        #Save to all_data
        ingredient = args.get("ingredient") or args.get("name") or args.get("query") or args.get("codes")
        if isinstance(ingredient, list):
            ingredient = ", ".join(map(str, ingredient))
        ingredient = str(ingredient).strip()

        if ingredient:
          if ingredient not in all_data:
            all_data[ingredient] = {}
          all_data[ingredient][name] = result

        #print("→ Result:", result)
      else:
        print("→ No handler for this function.")
else:
  print("No ingredients found in OCR text, extracting nutrition... ")



# -------------------------------------Formatter Model-------------------------------------

from typing import Text
import re, json
import textwrap

formatter_model = gemini.GenerativeModel(models['FORMATTER_MODEL'])

SCHEMA = app_config.FORMATTER_SCHEMA

# ---------- HELPERS ----------
def _fill_defaults(node, template):
    """Recursively add any missing keys from template into node."""
    if isinstance(template, dict):
        return {k: _fill_defaults(node.get(k) if isinstance(node, dict) else None, v)
                for k, v in template.items()}
    if isinstance(template, list):
        return node if node else template
    return node if node not in (None, "", []) else template

# ---------- MAIN FUNCTION ----------
def formatter(text: str, nutrition):
    schema_str = json.dumps(SCHEMA, indent=2)
    prompt = app_prompts.formatter_prompt(schema_str, text, nutrition)
    i = 0
    for _ in range(3):  # retry up to 3 times
        raw = formatter_model.generate_content(prompt).text.strip()
        raw = re.sub(r"^```json|^```|```$", "", raw).strip()  # strip fences, keep emojis
        try:
            parsed = json.loads(raw)
            return _fill_defaults(parsed, SCHEMA)
        except Exception:
          i+=1
          continue
    raise ValueError("Failed to produce valid JSON after 3 attempts")

# -------------------------------------Final Output-------------------------------------
final_output = formatter(all_data, cleaned_ocr)
# -------------------------------------Save Output to Json-------------------------------------
with open("output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Json Saved to output.json")

end = time.time()
print(f"Process ended. Total time taken: {end - start:.2f} seconds")


# Changes
# formatter prompt slightly changed (true/false -->"true"/"false")
# Added a new rule in the formatter prompt to avoid non-breaking hyphens
# Added a new rule in the formatter prompt to avoid non-standard characters
# Some comments are removed/added for clarity