def parse_warning_data(data: dict) -> dict:
    return {
        "warnings": data["warnings"].split("/"),
        "confidence_scores": data["confidence scores"].split("/"),
        "related_papers": data["related papers"].split("+")
    }


def fill_defaults(node, template):
  """Recursively add any missing keys from template into node."""
  if isinstance(template, dict):
    return {k: fill_defaults(node.get(k) if isinstance(node, dict) else None, v)
            for k, v in template.items()}
  if isinstance(template, list):
    return node if node else template
  return node if node not in (None, "", []) else template