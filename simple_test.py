#!/usr/bin/env python3
"""
Simplest possible test - directly calls Gemini API with logging
"""
import os
import sys
import json
import base64
import requests
from pathlib import Path
from datetime import datetime

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

print("\n" + "="*60)
print("🧪 Direct Gemini API Test with SystemPrompt.txt")
print("="*60 + "\n")

# Load API key
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("❌ Error: GEMINI_API_KEY not found")
    sys.exit(1)
print(f"✓ API key loaded: {api_key[:10]}...\n")

# Load SystemPrompt.txt
sys.path.insert(0, str(Path(__file__).parent / "api"))
from menu import load_system_prompt

system_prompt = load_system_prompt()
print(f"✓ SystemPrompt loaded ({len(system_prompt)} chars)\n")

# Load test image
image_path = Path(__file__).parent / "chinese menu test.jpg"
print(f"📁 Loading: {image_path.name}")
with open(image_path, 'rb') as f:
    image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
print(f"✓ Image loaded ({len(image_bytes)} bytes)\n")

# Build prompt
prompt = f"""{system_prompt}

Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
  "original_text": "all Chinese text from the menu, separated by newlines",
  "translated_text": "full English translation, preserving structure",
  "menu_items": [
    {{
      "chinese": "dish name",
      "pinyin": "pronunciation",
      "english": "translation",
      "price": "price if visible",
      "ingredients": ["ingredient 1", "ingredient 2"],
      "pork_alert": "Yes - Type" or "No",
      "beef_alert": "Yes - Type" or "No",
      "spiciness_level": "X/5 - Description",
      "cultural_details": "Brief fact",
      "health_category": "Healthy/Unhealthy - Oil Level",
      "regional_origin": "Province",
      "dietary_info": ["vegetarian", "halal", etc.]
    }}
  ]
}}

Provide ALL requested information in ONE response."""

# Call Gemini API
gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

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

print("="*60)
print("🌐 Calling Gemini API...")
print("="*60 + "\n")

start_time = datetime.now()

try:
    response = requests.post(
        f"{gemini_url}?key={api_key}",
        headers={"Content-Type": "application/json"},
        json=payload_data,
        timeout=30
    )
    response.raise_for_status()

    api_duration = (datetime.now() - start_time).total_seconds()
    print(f"✓ API responded in {api_duration:.2f}s\n")

    gemini_result = response.json()

    # Extract response
    if 'candidates' in gemini_result and len(gemini_result['candidates']) > 0:
        candidate = gemini_result['candidates'][0]
        if 'content' in candidate and 'parts' in candidate['content']:
            result_text = candidate['content']['parts'][0]['text'].strip()
            print(f"✓ Response length: {len(result_text)} chars\n")

            # Remove markdown if present
            if result_text.startswith('```'):
                print("🔧 Removing markdown blocks...")
                result_text = result_text.split('\n', 1)[1]
                result_text = result_text.rsplit('\n```', 1)[0]
                result_text = result_text.strip()

            # Parse JSON
            print("📊 Parsing JSON...\n")
            result_json = json.loads(result_text)

            menu_items = result_json.get('menu_items', [])

            print("="*60)
            print(f"✅ SUCCESS! Found {len(menu_items)} menu items")
            print("="*60 + "\n")

            for i, item in enumerate(menu_items[:3], 1):
                print(f"--- Dish {i} ---")
                print(f"Chinese: {item.get('chinese', 'N/A')}")
                print(f"Pinyin: {item.get('pinyin', 'N/A')}")
                print(f"English: {item.get('english', 'N/A')}")
                print(f"Spice: {item.get('spiciness_level', 'N/A')}")
                print(f"Pork: {item.get('pork_alert', 'N/A')}")
                print(f"Health: {item.get('health_category', 'N/A')}")
                print()

            if len(menu_items) > 3:
                print(f"... and {len(menu_items) - 3} more items\n")

            total_duration = (datetime.now() - start_time).total_seconds()
            print(f"⏱️  Total time: {total_duration:.2f}s")
        else:
            print("❌ Unexpected response format")
    else:
        print("❌ No response from Gemini")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
