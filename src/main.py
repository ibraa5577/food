from google import genai
from google.genai import types
import os
import google.generativeai as gemini
import json
import re, pandas as pd
import pandas as pd 
from fastapi.responses import JSONResponse
from fastapi import Request
from dotenv import load_dotenv
import time
import threading
from src import app_config, agent_tools, app_prompts, tool_schemas, ocr, helper_funcs
from fastapi import FastAPI, File, UploadFile
import re
import tempfile
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# -------------------------------------Setup & Configurations-------------------------------------
app = FastAPI(title="Kaust Project")

start = time.time()
print("Starting the process...")
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

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
# -------------------------------------Cleaning Model-------------------------------------
_CLEAN_CACHE = {}          # key -> (ts, data)
_CLEAN_TTL_OK = 24*3600    # 24h for successes
_CLEAN_TTL_ERR = 300       # 5m for errors

def _clean_key(s: str) -> str:
    # normalize & hash to keep memory small
    norm = (s or "").strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()

def clean_cache_get(s: str):
    k = _clean_key(s)
    v = _CLEAN_CACHE.get(k)
    if not v: return None
    ts, data, is_err = v
    ttl = _CLEAN_TTL_ERR if is_err else _CLEAN_TTL_OK
    return data if (time.time() - ts) < ttl else None

def clean_cache_set(s: str, data, is_err: bool):
    k = _clean_key(s)
    _CLEAN_CACHE[k] = (time.time(), data, is_err)

gemini.configure(api_key=GEMINI_API_KEY)
model = gemini.GenerativeModel(models['CLEANING_MODEL'])



# def extract_ingredients_and_nutrition(ocr_text: str) -> dict:
#   prompt = app_prompts.cleaning_prompt(ocr_text)
#   try:
#     response = model.generate_content(prompt)
#   except Exception as e:
#     return {"error": f"cleaning_model_failed: {e}"}
#   text = response.text.strip()

# #Remove code fences and non-ascii characters
#   text = re.sub(r"[^\x00-\x7F]+", "", text)
#   if text.startswith("```json"):
#     text = text.replace("```json", "").replace("```", "").strip()

#   try:
#     return json.loads(text)
#   except json.JSONDecodeError:
#     fix_prompt = f"Fix this to be valid JSON only, no explanations:\n{text}"
#     fixed = model.generate_content(fix_prompt).text.strip()
#     fixed = re.sub(r"[^\x00-\x7F]+", "", fixed)
#     try:
#       return json.loads(fixed)
#     except:
#       return {"error": "Invalid JSON", "raw": fixed}
# New Caching cleaner

def extract_ingredients_and_nutrition(ocr_text: str) -> dict:
  # 1) cache check
  cached = clean_cache_get(ocr_text)
  if cached is not None:
    return cached

  prompt = app_prompts.cleaning_prompt(ocr_text)
  try:
    response = model.generate_content(prompt)
    text = response.text.strip()
  except Exception as e:
    err = {"error": f"cleaning_model_failed: {e}"}
    clean_cache_set(ocr_text, err, is_err=True)
    return err

  # sanitize
  text = re.sub(r"[^\x00-\x7F]+", "", text)
  if text.startswith("```json"):
    text = text.replace("```json", "").replace("```", "").strip()

  # try parse
  try:
    data = json.loads(text)
    clean_cache_set(ocr_text, data, is_err=False)
    return data
  except json.JSONDecodeError:
    fix_prompt = f"Fix this to be valid JSON only, no explanations:\n{text}"
    try:
      fixed = model.generate_content(fix_prompt).text.strip()
      fixed = re.sub(r"[^\x00-\x7F]+", "", fixed)
      data = json.loads(fixed)
      clean_cache_set(ocr_text, data, is_err=False)
      return data
    except Exception:
      err = {"error": "Invalid JSON", "raw": (fixed if 'fixed' in locals() else text[:200])}
      clean_cache_set(ocr_text, err, is_err=True)
      return err
#cleaned_ocr = extract_ingredients_and_nutrition(OCR_text)
#print(json.dumps(cleaned_ocr, indent=2))


# -------------------------------------in-memory cache (tool, ingredient)-------------------------------------
_CACHE = {}  # (tool_name, normalized_ingredient) -> (timestamp, data)
_CACHE_TTL = 3600.0  # seconds
_CACHE_LOCK = threading.Lock()

def _norm(x: str) -> str:
  return (x or "").strip().lower()

def cache_get(tool: str, ingredient: str):
  k = (tool, _norm(ingredient))
  with _CACHE_LOCK:
    v = _CACHE.get(k)
  if not v:
    return None
  ts, data = v
  return data if (time.time() - ts) < _CACHE_TTL else None

def cache_set(tool: str, ingredient: str, data):
  k = (tool, _norm(ingredient))
  with _CACHE_LOCK:
    _CACHE[k] = (time.time(), data)


# -------------------------------------Agentic Model-------------------------------------
def run_agent_model(cleaned_ocr: dict) -> dict:
  if not cleaned_ocr.get('ingredients'): return {}
  client = genai.Client(api_key=GEMINI_API_KEY)
  schemas = types.Tool(function_declarations=tool_schemas.schema_list)
  config = types.GenerateContentConfig(tools=[schemas], temperature=0, seed=42)
  resp = client.models.generate_content(model='gemini-1.5-flash', contents=app_prompts.agent_prompt(cleaned_ocr), config=config)
  parts = resp.candidates[0].content.parts

  func_map = {
      "get_aliases": agent_tools.aliases,
      "get_e_number_info": agent_tools.e_number_info,
      "get_research_papers": agent_tools.research_papers,
      "get_warnings": agent_tools.warnings
  }
  out = defaultdict(dict)
    
  jobs, metas = [], []
  for p in parts:
    call = getattr(p, "function_call", None)
    if not call or call.name not in func_map:
      continue
    name, args = call.name, call.args
    ing = args.get("ingredient") or args.get("name") or args.get("query") or args.get("codes")
    if isinstance(ing, list):
      ing = ", ".join(map(str, ing))
    ing = (ing or "").strip().lower() or "_misc"

    # cache check
    cached = cache_get(name, ing)
    if cached is not None:
      out[ing][name] = cached
      continue

    jobs.append((name, args))
    metas.append((ing, name))
  if not jobs:
    return dict(out)
  max_workers = min(8, max(1, len(jobs)))
  with ThreadPoolExecutor(max_workers=max_workers) as ex:
    futures = {ex.submit(func_map[n], **a): (ing, n) for (n, a), (ing, n) in zip(jobs, metas)}
    for fut in as_completed(futures):
      ing, tool = futures[fut]
      try:
        res = fut.result()
        out[ing][tool] = res
        cache_set(tool, ing, res)
      except Exception as e:
        out[ing][tool] = {"error": str(e)}
  return dict(out)



# -------------------------------------Formatter Model-------------------------------------
formatter_model = gemini.GenerativeModel(models['FORMATTER_MODEL'])
SCHEMA = app_config.FORMATTER_SCHEMA

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
      return helper_funcs.fill_defaults(parsed, SCHEMA)
    except Exception:
      i+=1
      continue
  raise ValueError("Failed to produce valid JSON after 3 attempts")

# -------------------------------------Final Output-------------------------------------
# if __name__ == "__main__":
#   # -------- Standalone script mode (kept for local runs) --------
#   all_data = run_agent_model(cleaned_ocr)   # define all_data first
#   final_output = formatter(all_data, cleaned_ocr)
#   with open("output.json", "w") as f:
#     json.dump(final_output, f, indent=2)
#   print("Json Saved to output.json")

#   end = time.time()
#   print(f"Process ended. Total time taken: {end - start:.2f} seconds")


# API Endpoints
@app.post("/process-image")
async def process_image(file: UploadFile = File(...)):

  raw = await file.read()
  
  ext = os.path.splitext(file.filename or "")[1] or ".png"
  with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
    tmp.write(raw)
    tmp_path = tmp.name

  try:
    ocr_out = ocr.run_ocr(tmp_path, min_confidence=0.7)
    ocr_text = ocr_out.get("full_text") if isinstance(ocr_out, dict) else ocr_out

    # Main Pipeline
    cleaned = extract_ingredients_and_nutrition(ocr_text)
    if "error" in cleaned:
      return {"error": "cleaning_failed", "details": cleaned}
    all_data = run_agent_model(cleaned)
    try:
      final_output = formatter(all_data, cleaned)
    except Exception as e:
      return {"error": f"formatter_failed: {e}", "cleaned": cleaned, "all_data": all_data}
    return final_output
  finally:
    #Cleanup temporary file
    try:
      os.remove(tmp_path)
    except OSError:
      pass


@app.get("/")
def root():
  return {"service": "Kaust Project", "status": "ok"}

@app.get("/health")
def health():
  return {"ok": True}


@app.exception_handler(Exception)
async def _err_json(_: Request, exc: Exception):
  return JSONResponse(status_code=500, content={"error": str(exc)})
