import requests
import helper_funcs
import pandas as pd
import urllib.parse
import re
import json
import app_config
import requests
import html

warning_df = pd.read_csv(app_config.warnings_path).set_index("ingredient")
warning_df.index = warning_df.index.astype(str).str.strip().str.lower()
relevant_keywords = [
    # Core food/health context
    'food', 'nutrition', 'diet', 'consumption', 'health', 'metabolism',

    # Common health-related impacts
    'toxicity', 'safety', 'risk', 'exposure', 'cancer', 'obesity', 'diabetes',
    'allergy', 'inflammation', 'fertility', 'reproductive',

    # Regulatory / classification
    'additive', 'preservative', 'sweetener', 'coloring', 'regulation', 'approved',
    'GRAS', 'EFSA', 'FDA',

    # Study types & context
    'clinical', 'trial', 'meta-analysis', 'review', 'animal study', 'biomarker'
]

#=========================== Tools ===========================
# Function
# Schema

#=========================== Aliases ===========================
def aliases(name: str, top: int = 20) -> list[str]:
    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    url  = f"{base}/compound/name/{urllib.parse.quote(name)}/synonyms/JSON"
    resp = requests.get(url, timeout=20).json()
    if "InformationList" not in resp:   # if compound not found
        return []
    syns = resp['InformationList']['Information'][0].get('Synonym', [])
    return syns[:top][:5]



#=========================== E-Number ===========================
def e_number_info(codes: list[str], csv_path: str = app_config.e_numbers_path) -> dict[str, dict]:
    df = pd.read_csv(csv_path)
    df["E-code"] = df["E-code"].str.upper().str.replace(r"\s+", "", regex=True)

    info = {}
    for c in codes:
        c_clean = re.sub(r"\s+", "", c.upper())
        row = df[df["E-code"] == c_clean]
        if not row.empty:
            info[c_clean] = {
                "name":    row.iloc[0]["Name"],
                "purpose": row.iloc[0]["Purpose"],
                "status":  row.iloc[0]["Status"],
            }
    return info




#=========================== Research Papers ===========================

API_BASE = "https://api.openalex.org/works"
EMAIL = "xxibxxx9@gmail.com"

def research_papers(
    ingredient: str,
    top: int = 3,
) -> list[tuple[str, str]]:

    params = {
        "search": f'{ingredient} in food and health',
        "per-page": top * 5,  # overfetch to allow room for filtering/sorting
        "mailto": EMAIL,
    }

    try:
        resp = requests.get(API_BASE, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        scored_results = []
        for item in data.get("results", []):
            if item.get("language") != "en":
                continue
            if not item.get("open_access", {}).get("is_oa", False):
                continue

            concepts = item.get("concepts", [])
            keywords = item.get("keywords", [])

            score = sum(c.get("score", 0) for c in concepts if c.get("score", 0) >= 0.3)
            score += sum(k.get("score", 0) for k in keywords if k.get("score", 0) >= 0.3)

            if score > 0:
                title = item.get("display_name")
                # if title:
                #     title = html.unescape(title)  
                #     title = re.sub(r"<[^>]+>", "", title)
                doi = item.get("doi") or item.get("ids", {}).get("doi")
                if title and doi:
                    scored_results.append((score, title, doi))

        scored_results.sort(reverse=True)
        return [(title, doi) for score, title, doi in scored_results[:top]]

    except requests.RequestException as e:
        print("OpenAlex request error:", e)
        return []


#=========================== Get Warnings ===========================
def warnings(ingredient):
  if ingredient.lower() in warning_df.index:
    warnings_data = warning_df.loc[ingredient.lower()].to_dict()
    return helper_funcs.parse_warning_data(warnings_data)
  else:
    return {"warnings": [], "confidence scores": [], "related papers": []}


#=========================== Get Allergens ===========================
def allergens(ing):
  pass

#=========================== Get Health Score ===========================
def health_score(ing):
  pass




