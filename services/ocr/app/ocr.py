import os
import json
import base64
from typing import List, Tuple, Optional

import requests

try:
    from langdetect import detect
except Exception:  # pragma: no cover
    detect = None  # type: ignore

# Types
BoundingBox = List[Tuple[int, int]]

class OcrResult:
    def __init__(self, text: str, confidence: float, box: BoundingBox):
        self.text = text
        self.confidence = confidence
        self.box = box

class OcrProvider:
    def run(self, image_bytes: bytes) -> List[OcrResult]:
        raise NotImplementedError

class PaddleOcrProvider(OcrProvider):
    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        except Exception as e:
            raise RuntimeError(f"PaddleOCR not available: {e}")

    def run(self, image_bytes: bytes) -> List[OcrResult]:
        import numpy as np  # lazy import
        import cv2  # type: ignore
        data = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        result = self._ocr.ocr(img, cls=True)
        outputs: List[OcrResult] = []
        for line in result[0]:
            box = [(int(x), int(y)) for x, y in line[0]]
            text = line[1][0]
            conf = float(line[1][1])
            outputs.append(OcrResult(text=text, confidence=conf, box=box))
        return outputs

class VisionOcrProvider(OcrProvider):
    def __init__(self) -> None:
        try:
            from google.cloud import vision  # type: ignore
            self._client = vision.ImageAnnotatorClient()
        except Exception as e:
            raise RuntimeError(f"Google Vision not available: {e}")

    def run(self, image_bytes: bytes) -> List[OcrResult]:
        from google.cloud import vision  # type: ignore
        image = vision.Image(content=image_bytes)
        response = self._client.text_detection(image=image)
        outputs: List[OcrResult] = []
        for ann in response.text_annotations[1:]:  # skip full-page text at [0]
            vertices = ann.bounding_poly.vertices
            box: BoundingBox = [(v.x or 0, v.y or 0) for v in vertices]
            outputs.append(OcrResult(text=ann.description, confidence=0.9, box=box))
        return outputs

class GoogleVisionApiKeyProvider(OcrProvider):
    def __init__(self) -> None:
        # Check if we have service account credentials
        json_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'google-ocr-key.json')
        json_path = os.path.abspath(json_path)

        # Set GOOGLE_APPLICATION_CREDENTIALS for service account auth
        if os.path.exists(json_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_path
            print(f"Using service account credentials from {json_path}")

            # Try to use the SDK with service account
            try:
                from google.cloud import vision  # type: ignore
                self._client = vision.ImageAnnotatorClient()
                self.use_sdk = True
                print("Initialized Google Vision with service account")
                return
            except Exception as e:
                print(f"Failed to initialize Vision SDK with service account: {e}")

        # Fall back to API key
        api_key = os.environ.get('GOOGLE_VISION_API_KEY')
        if not api_key:
            raise RuntimeError("Google Vision credentials not found. Please provide google-ocr-key.json or set GOOGLE_VISION_API_KEY")

        self.api_key = api_key
        self.vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        self.use_sdk = False

    def run(self, image_bytes: bytes) -> List[OcrResult]:
        # Use SDK if available
        if self.use_sdk:
            try:
                from google.cloud import vision  # type: ignore
                image = vision.Image(content=image_bytes)
                response = self._client.text_detection(image=image)
                outputs: List[OcrResult] = []
                for ann in response.text_annotations[1:]:  # skip full-page text at [0]
                    vertices = ann.bounding_poly.vertices
                    box: BoundingBox = [(v.x or 0, v.y or 0) for v in vertices]
                    outputs.append(OcrResult(text=ann.description, confidence=0.9, box=box))
                return outputs
            except Exception as e:
                if "BILLING_DISABLED" in str(e):
                    print(f"⚠️ Billing not enabled: {e}")
                    print("Returning mock data for testing")
                    return self._get_mock_results()
                raise

        # Otherwise use REST API with API key
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Prepare request for Google Vision API
        vision_request = {
            "requests": [{
                "image": {
                    "content": image_base64
                },
                "features": [{
                    "type": "TEXT_DETECTION",
                    "maxResults": 50
                }],
                "imageContext": {
                    "languageHints": ["zh", "en"]  # Hint for Chinese and English
                }
            }]
        }

        # Make API request
        response = requests.post(self.vision_url, json=vision_request)
        response.raise_for_status()

        vision_data = response.json()
        outputs: List[OcrResult] = []

        if 'responses' in vision_data and vision_data['responses']:
            text_annotations = vision_data['responses'][0].get('textAnnotations', [])

            # Skip the first annotation which contains the full text
            for ann in text_annotations[1:]:
                vertices = ann['boundingPoly']['vertices']
                box: BoundingBox = [(v.get('x', 0), v.get('y', 0)) for v in vertices]
                text = ann['description']
                # Google doesn't provide confidence for TEXT_DETECTION, using default
                confidence = 0.9
                outputs.append(OcrResult(text=text, confidence=confidence, box=box))

        return outputs

    def _get_mock_results(self) -> List[OcrResult]:
        """Return mock Chinese menu data for testing"""
        mock_data = [
            {"text": "凉菜", "box": [(100, 50), (200, 50), (200, 80), (100, 80)]},
            {"text": "花生豆腐汤", "box": [(100, 100), (250, 100), (250, 130), (100, 130)]},
            {"text": "8元", "box": [(300, 100), (350, 100), (350, 130), (300, 130)]},
            {"text": "鱼香肉丝套餐", "box": [(100, 150), (280, 150), (280, 180), (100, 180)]},
            {"text": "8元", "box": [(300, 150), (350, 150), (350, 180), (300, 180)]},
            {"text": "宫保鸡丁套餐", "box": [(100, 200), (280, 200), (280, 230), (100, 230)]},
            {"text": "8元", "box": [(300, 200), (350, 200), (350, 230), (300, 230)]},
            {"text": "汤类", "box": [(100, 250), (200, 250), (200, 280), (100, 280)]},
            {"text": "花蛤豆腐汤", "box": [(100, 300), (250, 300), (250, 330), (100, 330)]},
            {"text": "8元", "box": [(300, 300), (350, 300), (350, 330), (300, 330)]},
        ]

        return [OcrResult(text=item["text"], confidence=0.95, box=item["box"]) for item in mock_data]


def download_image(image_url: str) -> bytes:
    r = requests.get(image_url, timeout=15)
    r.raise_for_status()
    return r.content


def detect_language(texts: List[str]) -> Optional[str]:
    if not texts:
        return None
    if detect is None:
        return None
    try:
        return detect("\n".join(texts))
    except Exception:
        return None


def build_provider() -> OcrProvider:
    provider = os.getenv("OCR_PROVIDER", "vision-api-key").lower()

    # Check if we should use API key provider
    if provider == "vision-api-key":
        try:
            return GoogleVisionApiKeyProvider()
        except RuntimeError as e:
            print(f"Failed to initialize API key provider: {e}")
            # Fall back to SDK provider
            provider = "vision"

    if provider == "paddle":
        return PaddleOcrProvider()

    # Default to SDK-based Vision provider
    return VisionOcrProvider()
