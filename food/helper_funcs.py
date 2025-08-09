


def parse_warning_data(data: dict) -> dict:
    return {
        "warnings": data["warnings"].split("/"),
        "confidence_scores": data["confidence scores"].split("/"),
        "related_papers": data["related papers"].split("+")
    }