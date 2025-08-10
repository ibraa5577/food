aliases_schema = {
    "name": "get_aliases",
    "description": "Fetches known chemical synonyms for a compound using PubChem.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The compound name to search for, e.g., 'Calcium citrate'.",
            },
            "top": {
                "type": "integer",
                "description": "The maximum number of synonyms to return (default: 20).",
            },
        },
        "required": ["name"],
    },
}

e_number_schema = {
    "name": "get_e_number_info",
    "description": "Retrieves the common name, purpose (e.g. Sweetener), and regulatory status of one or more E‑number food additives.",
    "parameters": {
        "type": "object",
        "properties": {
            "codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of E‑numbers to look up, e.g., ['E100', 'E160b', 'E220']."
            }
        },
        "required": ["codes"],
    },
}

research_papers_schema = {
    "name": "get_research_papers",
    "description": "Retrieves research paper titles and DOIs related to a food ingredient from public API",
    "parameters": {
        "type": "object",
        "properties": {
            "ingredient": {
                "type": "string",
                "description": "The name of the ingredient to search for, e.g., 'aspartame', 'palm oil', 'sodium benzoate'."
            },
            "top": {
                "type": "integer",
                "description": "The number of top results to return from each source (default: 5, max: 10).",
                "default": 3,
                "minimum": 1,
                "maximum": 4
            }
        },
        "required": ["ingredient"]
    }
}


warnings_schema = {
    "name": "get_warnings",
    "description": "Retrieves health warnings, confidence levels, and related papers for a specific food ingredient based on internal risk assessments.",
    "parameters": {
        "type": "object",
        "properties": {
            "ingredient": {
                "type": "string",
                "description": "The name of the ingredient to retrieve warnings for, e.g., 'aspartame', 'annatto', 'sodium nitrite'."
            }
        },
        "required": ["ingredient"]
    }
}

schema_list = [aliases_schema, e_number_schema, research_papers_schema, warnings_schema]