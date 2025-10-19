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

class DishDetailsRequest(BaseModel):
    chinese_name: str
    english_name: str
    pinyin: Optional[str] = None

class BatchDishDetailsRequest(BaseModel):
    dishes: List[DishDetailsRequest]

class OcrRequest(BaseModel):
    image_url: Optional[str] = None
    image: Optional[str] = None  # base64 encoded image
    target_lang: Optional[str] = "en"

class MenuItem(BaseModel):
    chinese: str
    pinyin: Optional[str] = None  # Pinyin pronunciation
    english: str
    price: Optional[str] = None
    cultural_details: Optional[str] = None
    ingredients: Optional[List[str]] = None
    spiciness_level: Optional[str] = None  # "mild", "medium", "hot", "very hot"
    dietary_info: Optional[List[str]] = None  # ["vegetarian", "vegan", "halal", "gluten-free", etc.]
    regional_origin: Optional[str] = None
    recommended_pairings: Optional[List[str]] = None
    nutritional_info: Optional[str] = None

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

        # Use Gemini REST API directly with base64
        api_key = load_gemini_api_key()
        if not api_key:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        # Convert image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Prepare Gemini API request
        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

        headers = {
            "Content-Type": "application/json",
        }

        prompt = f"""Extract all text from this Chinese menu image and translate it to {payload.target_lang or 'English'}.

This is a QUICK extraction - just get the basic information for speed.

Return ONLY a JSON object with this exact structure (no markdown formatting):
{{
  "original_text": "all the Chinese text you found, separated by newlines",
  "translated_text": "the English translation, preserving the structure",
  "menu_items": [
    {{
      "chinese": "dish name in Chinese",
      "pinyin": "pinyin pronunciation with tone marks (e.g., Gōngbǎo Jīdīng)",
      "english": "dish name in English",
      "price": "price if found"
    }}
  ]
}}

Make sure to:
1. Extract ALL visible text from the menu quickly
2. Preserve the structure (sections, items, prices)
3. Provide accurate pinyin pronunciation with tone marks for each dish name
4. Return valid JSON only (no markdown code blocks)
5. BE FAST - only basic info needed now, details will be fetched separately"""

        payload_data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }]
        }

        # Make API request
        import requests
        response = requests.post(
            f"{gemini_url}?key={api_key}",
            headers=headers,
            json=payload_data
        )
        response.raise_for_status()
        gemini_result = response.json()

        # Parse Gemini's response
        if 'candidates' in gemini_result and len(gemini_result['candidates']) > 0:
            candidate = gemini_result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                result_text = candidate['content']['parts'][0]['text'].strip()
            else:
                raise HTTPException(status_code=500, detail="Unexpected Gemini response format")
        else:
            raise HTTPException(status_code=500, detail="No response from Gemini")

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

@app.post("/batch-dish-details")
async def batch_dish_details_endpoint(payload: BatchDishDetailsRequest):
    """Get detailed information for multiple dishes in one call"""
    try:
        api_key = load_gemini_api_key()
        if not api_key:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

        # Build list of dishes
        dishes_list = "\n".join([
            f"{i+1}. {dish.chinese_name} ({dish.pinyin if dish.pinyin else ''}) - {dish.english_name}"
            for i, dish in enumerate(payload.dishes)
        ])

        prompt = f"""Provide comprehensive details for these {len(payload.dishes)} Chinese dishes. Be concise.

Dishes:
{dishes_list}

Return ONLY a JSON array with this exact structure (no markdown):
[
  {{
    "cultural_details": "brief background (1-2 sentences)",
    "ingredients": ["main", "ingredients"],
    "spiciness_level": "none/mild/medium/hot/very hot",
    "dietary_info": ["vegetarian", "vegan", "halal", "gluten-free", etc.],
    "regional_origin": "province/region",
    "recommended_pairings": ["pairings"],
    "nutritional_info": "brief overview"
  }}
]

Return valid JSON array with {len(payload.dishes)} objects in the same order. No markdown."""

        payload_data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        import requests
        response = requests.post(
            f"{gemini_url}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload_data
        )
        response.raise_for_status()
        gemini_result = response.json()

        if 'candidates' in gemini_result and len(gemini_result['candidates']) > 0:
            candidate = gemini_result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                result_text = candidate['content']['parts'][0]['text'].strip()
            else:
                raise HTTPException(status_code=500, detail="Unexpected Gemini response format")
        else:
            raise HTTPException(status_code=500, detail="No response from Gemini")

        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('\n```', 1)[0]
            result_text = result_text.strip()

        result_json = json.loads(result_text)
        return {"details": result_json}

    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse response: {str(e)}")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dish-details")
async def dish_details_endpoint(payload: DishDetailsRequest):
    """Get detailed information about a specific dish"""
    try:
        api_key = load_gemini_api_key()
        if not api_key:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

        prompt = f"""Provide comprehensive details about this Chinese dish:
Chinese name: {payload.chinese_name}
English name: {payload.english_name}
{f'Pinyin: {payload.pinyin}' if payload.pinyin else ''}

Return ONLY a JSON object with this exact structure (no markdown formatting):
{{
  "cultural_details": "brief cultural/historical background of this dish (2-3 sentences)",
  "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
  "spiciness_level": "none/mild/medium/hot/very hot",
  "dietary_info": ["vegetarian", "vegan", "halal", "gluten-free", "dairy-free", "contains nuts", etc.],
  "regional_origin": "region/province in China where this dish originated",
  "recommended_pairings": ["rice", "noodles", "soup", "tea", etc.],
  "nutritional_info": "brief overview (e.g., high protein, low fat, etc.)"
}}

Be accurate and concise. Return valid JSON only (no markdown code blocks)."""

        payload_data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        import requests
        response = requests.post(
            f"{gemini_url}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload_data
        )
        response.raise_for_status()
        gemini_result = response.json()

        if 'candidates' in gemini_result and len(gemini_result['candidates']) > 0:
            candidate = gemini_result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                result_text = candidate['content']['parts'][0]['text'].strip()
            else:
                raise HTTPException(status_code=500, detail="Unexpected Gemini response format")
        else:
            raise HTTPException(status_code=500, detail="No response from Gemini")

        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('\n```', 1)[0]
            result_text = result_text.strip()

        result_json = json.loads(result_text)
        return result_json

    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse response: {str(e)}")
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
