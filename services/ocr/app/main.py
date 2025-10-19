import os
import json
import base64
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import google.generativeai as genai

class TranslateRequest(BaseModel):
    text: str
    target: str

class OcrRequest(BaseModel):
    image_url: Optional[str] = None
    image: Optional[str] = None  # base64 encoded image
    target_lang: Optional[str] = "en"

class MenuItem(BaseModel):
    chinese: str
    english: str
    price: Optional[str] = None

class OcrResponse(BaseModel):
    original_text: str
    translated_text: str
    menu_items: Optional[List[MenuItem]] = None
    detected_lang: str = "zh"

app = FastAPI(title="MenuGen OCR Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
def load_gemini_api_key():
    """Load Gemini API key from JSON file"""
    key_file = Path(__file__).parent.parent.parent.parent / "gemini_api_key.json"
    if key_file.exists():
        with open(key_file) as f:
            config = json.load(f)
            return config.get("api_key")
    return None

@app.on_event("startup")
def startup_event():
    api_key = load_gemini_api_key()
    if api_key:
        genai.configure(api_key=api_key)
        print("✅ Gemini API initialized successfully")
    else:
        print("⚠️ Gemini API key not found. Please add gemini_api_key.json")

@app.post("/ocr", response_model=OcrResponse)
async def ocr_endpoint(payload: OcrRequest):
    try:
        # Get image data
        if payload.image:
            # Remove data URL prefix if present
            image_data = payload.image
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        elif payload.image_url:
            import requests
            response = requests.get(payload.image_url, timeout=15)
            response.raise_for_status()
            image_bytes = response.content
        else:
            raise HTTPException(status_code=400, detail="Either image or image_url must be provided")

        # Use Gemini to extract and translate in one call
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""Extract all text from this Chinese menu image and translate it to {payload.target_lang or 'English'}.

Return ONLY a JSON object with this exact structure (no markdown formatting):
{{
  "original_text": "all the Chinese text you found, separated by newlines",
  "translated_text": "the English translation, preserving the structure",
  "menu_items": [
    {{"chinese": "dish name in Chinese", "english": "dish name in English", "price": "price if found"}}
  ]
}}

Make sure to:
1. Extract ALL visible text from the menu
2. Preserve the structure (sections, items, prices)
3. Return valid JSON only (no markdown code blocks)"""

        # Send image to Gemini
        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(image_bytes))

        response = model.generate_content([prompt, image])

        # Parse Gemini's response
        result_text = response.text.strip()

        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('\n```', 1)[0]
            result_text = result_text.strip()

        result_json = json.loads(result_text)

        return OcrResponse(
            original_text=result_json.get("original_text", ""),
            translated_text=result_json.get("translated_text", ""),
            menu_items=[MenuItem(**item) for item in result_json.get("menu_items", [])],
            detected_lang="zh"
        )

    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Response was: {result_text}")
        raise HTTPException(status_code=500, detail=f"Failed to parse Gemini response: {str(e)}")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate")
def translate_endpoint(payload: TranslateRequest):
    """Simple translation endpoint - returns mock translation for now"""
    try:
        # Mock translation for testing
        # In production, you would use Google Translate API or similar
        translated = f"[EN] {payload.text[:100]}"

        # Basic translation hints based on common Chinese menu items
        translations = {
            "凉菜": "Cold Dishes",
            "花生豆腐汤": "Peanut Tofu Soup",
            "元": "Yuan",
            "8元": "8 Yuan",
            "鱼香肉丝套餐": "Fish-Flavored Shredded Pork Set",
            "宫保鸡丁套餐": "Kung Pao Chicken Set",
            "汤类": "Soups",
            "花蛤豆腐汤": "Clam Tofu Soup",
        }

        # Try to match common phrases
        for chinese, english in translations.items():
            if chinese in payload.text:
                translated = payload.text
                for cn, en in translations.items():
                    translated = translated.replace(cn, en)
                break

        return {"success": True, "translatedText": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
