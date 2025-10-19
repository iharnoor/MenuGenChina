from pydantic import BaseModel, HttpUrl, Field
from typing import List, Tuple, Optional, Union

BoundingBox = List[Tuple[int, int]]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

class OcrRequest(BaseModel):
    image_url: Optional[HttpUrl] = None
    image: Optional[str] = None  # base64 encoded image
    target_lang: Optional[str] = None  # e.g., 'en'

class OcrLine(BaseModel):
    text: str
    confidence: float
    box: BoundingBox
    translated: Optional[str] = None

class OcrResponse(BaseModel):
    detected_lang: Optional[str]
    lines: List[OcrLine]
