import os
from functools import lru_cache
from typing import Dict, Any, List, Optional, Union
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

class AzureOCR:
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None):
        endpoint = endpoint or os.getenv("VISION_ENDPOINT")
        key = key or os.getenv("VISION_KEY")
        if not endpoint or not key:
            raise ValueError("VISION_ENDPOINT and VISION_KEY must be set.")
        self.client = ImageAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    def analyze_image(
        self,
        image: Union[str, bytes],        # file path OR raw bytes
        *, is_url: bool = False,
        min_confidence: float = 0.0
    ) -> Dict[str, Any]:
        """
        Returns JSON-friendly dict:
        {
          'full_text': str,
          'blocks': [
             {'lines': [
               {'text': str, 'confidence': float, 'bbox': [{'x':int,'y':int},...],
                'words': [{'text':str,'confidence':float,'polygon':[{'x':, 'y':}, ...]}]
               }, ...
             ]}
          ]
        }
        """
        try:
            if is_url:
                result = self.client.analyze(image_url=image, visual_features=[VisualFeatures.READ])
            else:
                if isinstance(image, str):
                    with open(image, "rb") as f:
                        result = self.client.analyze(image_data=f, visual_features=[VisualFeatures.READ])
                else:
                    result = self.client.analyze(image_data=image, visual_features=[VisualFeatures.READ])
        except HttpResponseError as e:
            return {"error": str(e), "status_code": getattr(e, "status_code", None)}

        output: Dict[str, Any] = {"full_text": "", "blocks": []}
        if result.read is None or not result.read.blocks:
            return output

        full_text_lines: List[str] = []
        for block in result.read.blocks:
            block_dict = {"lines": []}
            for line in block.lines or []:
                kept_words = [
                    {
                        "text": w.text,
                        "confidence": float(w.confidence or 0.0),
                        "polygon": [{"x": p["x"], "y": p["y"]} for p in (w.bounding_polygon or [])],
                    }
                    for w in (line.words or [])
                    if (w.confidence or 0.0) >= min_confidence
                ]
                if not kept_words:
                    continue
                line_text = " ".join(w["text"] for w in kept_words)
                full_text_lines.append(line_text)
                avg_conf = sum(w["confidence"] for w in kept_words) / len(kept_words)
                block_dict["lines"].append({
                    "text": line_text,
                    "confidence": avg_conf,
                    "bbox": [{"x": p["x"], "y": p["y"]} for p in (line.bounding_polygon or [])],
                    "words": kept_words,
                })
            if block_dict["lines"]:
                output["blocks"].append(block_dict)

        output["full_text"] = "\n".join(full_text_lines).strip()
        return output

@lru_cache(maxsize=1)
def _singleton() -> AzureOCR:
    # Reuse one client per process
    return AzureOCR()

def run_ocr(image: Union[str, bytes], *, is_url: bool = False, min_confidence: float = 0.0) -> Dict[str, Any]:
    return _singleton().analyze_image(image, is_url=is_url, min_confidence=min_confidence)
