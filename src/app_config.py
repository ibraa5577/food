# Models
models = {
    "CLEANING_MODEL": "gemini-1.5-flash",
    "AGENT_MODEL": "gemini-1.5-flash",
    "FORMATTER_MODEL": "gemini-1.5-flash"
}


# Local DBs Paths
warnings_path = "src/data/Warnings.csv"
e_numbers_path = "src/data/E Numbers.csv"

# Other Configurations
FORMATTER_SCHEMA = {
  "serving_information": {
    "serving_size": "",
    "servings_per_container": 0.0
  },
  "nutritional_facts": {
    "calories": 0.0,
    "protein": 0.0,
    "carbohydrate": {
      "total": 0.0,
      "dietary_fiber": 0.0,
      "total_sugars": 0.0,
      "added_sugars": 0.0
    },
    "fat": {
      "total": 0.0,
      "saturated_fat": 0.0,
      "trans_fat": 0.0
    }
  },
  "micronutrients": [
    {
      "name": "",
      "value": 0.0,
      "unit": ""
    }
  ],
  "ingredients": [
    {
      "name": "",
      "description": "",
      "category": "",
      "other_names": [],
      "safety": {
        "warnings": [],
        "allergens": []
      },
      "banned": "false",
      "research_papers": [
        {
          "title": "",
          "doi": ""
        }
      ]
    }
  ],
  "notes": {
    "positive": [],
    "neutral": [],
    "negative": [],
    "critical": []
  }
}
