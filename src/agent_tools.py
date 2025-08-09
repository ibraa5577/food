import requests
import helper_funcs
import pandas as pd
import urllib.parse
import re
import json


# Function
# Schema

warning_df = pd.read_csv("data/Warnings.csv").set_index("ingredient")
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
#=========================== Aliases ===========================
def aliases(name: str, top: int = 20) -> list[str]:
    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    url  = f"{base}/compound/name/{urllib.parse.quote(name)}/synonyms/JSON"
    resp = requests.get(url, timeout=10).json()
    if "InformationList" not in resp:   # if compound not found
        return []
    syns = resp['InformationList']['Information'][0].get('Synonym', [])
    return syns[:top][:5]



#=========================== E-Number ===========================
def e_number_info(codes: list[str], csv_path: str = "data/E Numbers.csv") -> dict[str, dict]:
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




#=========================== Safety ===========================


#=========================== Research Papers ===========================

def research_papers(ingredient: str, top: int = 5) -> list[tuple[str, str]]:
    results = []

    def is_relevant(title: str, ingredient: str) -> bool:
        title_lower = title.lower()
        return (
            ingredient.lower() in title_lower and
            any(keyword in title_lower for keyword in relevant_keywords)
        )

    # Crossref API
    try:
        query_cr = f"{ingredient} food nutrition health metabolism additive"
        url_cr = f"https://api.crossref.org/works?query={query_cr}&rows={top}"
        headers = {"User-Agent": "IbrahimResearchBot/1.0 (mailto:abrahymalshay5@gmail.com)"}
        cr_resp = requests.get(url_cr, headers=headers, timeout=20).json()
        cr_items = cr_resp.get("message", {}).get("items", [])
        for item in cr_items:
            title = item.get("title", [""])[0]
            doi = item.get("DOI", "")
            if title and doi and is_relevant(title, ingredient):
                results.append((title, doi))
    except Exception as e:
        print("Crossref error:", e)

    # Semantic Scholar API
    try:
        query_ss = f"{ingredient} ingredient"
        url_ss = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query_ss,
            "fields": "title,doi",
            "limit": top
        }
        ss_resp = requests.get(url_ss, params=params, timeout=20).json()
        for item in ss_resp.get("data", []):
            title = item.get("title", "")
            doi = item.get("doi", "")
            if title and doi and is_relevant(title, ingredient):
                results.append((title, doi))
    except Exception as e:
        print("Semantic Scholar error:", e)

    return results






#=========================== ADI ===========================



#=========================== Ingredient Description ===========================
def ing_desc(ing):
  pass

#=========================== Get Warnings ===========================
def warnings(ingredient):
  if ingredient.lower() in warning_df.index:
    warnings_data = warning_df.loc[ingredient].to_dict()
    return helper_funcs.parse_warning_data(warnings_data)
  else:
    return {"warnings": [], "confidence scores": [], "related papers": []}



#=========================== Get Allergens ===========================
def allergens(ing):
  pass

#=========================== Get Health Score ===========================
def health_score(ing):
  pass




