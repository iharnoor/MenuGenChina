import os
import json
import base64
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import requests
from pathlib import Path
from datetime import datetime
import sys

def load_system_prompt():
    """Load the system prompt from SystemPrompt.txt"""
    # Try to load from parent directory (when deployed on Vercel)
    prompt_path = Path(__file__).parent.parent / "SystemPrompt.txt"
    if not prompt_path.exists():
        # Fallback to current directory
        prompt_path = Path(__file__).parent / "SystemPrompt.txt"

    if prompt_path.exists():
        content = prompt_path.read_text(encoding='utf-8').strip()
        print(f"  📝 Loaded SystemPrompt.txt ({len(content)} chars) from: {prompt_path}", file=sys.stderr, flush=True)
        return content
    else:
        print(f"  ⚠️  SystemPrompt.txt not found, using fallback prompt", file=sys.stderr, flush=True)
        # Fallback prompt if file not found
        return """From the attached image of the Chinese menu, please translate the items and provide:
Pinyin Name, English Translation, Core Ingredients, Pork Alert, Beef Alert, Spice Level, Cultural Element, Health Category"""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            start_time = datetime.now()
            print(f"  📥 Parsing request body...", file=sys.stderr, flush=True)

            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))
            print(f"  ✓ Request parsed ({content_length} bytes)", file=sys.stderr, flush=True)

            # Get Gemini API key from environment
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                print(f"  ❌ Error: GEMINI_API_KEY not configured", file=sys.stderr, flush=True)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'GEMINI_API_KEY not configured'}).encode())
                return

            print(f"  ✓ API key loaded (length: {len(api_key)} chars)", file=sys.stderr, flush=True)

            # Get batch number for progressive loading (default to batch 1)
            batch_number = payload.get('batch_number', 1)
            dishes_per_batch = 2
            start_dish = (batch_number - 1) * dishes_per_batch + 1
            end_dish = start_dish + dishes_per_batch - 1
            print(f"  📦 Processing batch {batch_number} (dishes {start_dish}-{end_dish})...", file=sys.stderr, flush=True)

            # Get image data
            print(f"  🖼️  Decoding image data...", file=sys.stderr, flush=True)
            image_data = payload.get('image', '')
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            print(f"  ✓ Image decoded ({len(image_bytes)} bytes)", file=sys.stderr, flush=True)

            # Prepare Gemini API request
            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

            target_lang = payload.get('target_lang', 'en')

            # Load system prompt from SystemPrompt.txt
            system_prompt = load_system_prompt()

            # Create batch-specific prompt
            batch_instruction = f"""IMPORTANT: Only analyze dishes {start_dish} to {end_dish} from this menu.
Skip all dishes before dish {start_dish} and after dish {end_dish}.
Count dishes from top to bottom, left to right as they appear on the menu.
If there are fewer than {end_dish} dishes total, return only what exists and set has_more to false."""

            # Combine with JSON structure for batch-specific API call
            prompt = f"""{system_prompt}

{batch_instruction}

Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
  "original_text": "Chinese text for dishes {start_dish}-{end_dish} only",
  "translated_text": "English translation for dishes {start_dish}-{end_dish} only",
  "menu_items": [
    {{
      "chinese": "dish name in Chinese characters",
      "pinyin": "Pinyin pronunciation with tone marks",
      "english": "English translation",
      "price": "price if visible",
      "ingredients": ["main ingredient 1", "ingredient 2", "ingredient 3"],
      "pork_alert": "Yes - Type" or "No",
      "beef_alert": "Yes - Type" or "No",
      "spiciness_level": "X/5 - Description",
      "cultural_details": "Brief engaging fact",
      "health_category": "Healthy/Unhealthy - Oil Level",
      "regional_origin": "Province or region",
      "dietary_info": ["vegetarian", "halal", etc.]
    }}
  ],
  "has_more": true or false (are there more dishes after {end_dish}?),
  "total_dishes_estimate": approximate total number of dishes on entire menu
}}

Provide ALL requested information for dishes {start_dish}-{end_dish} ONLY. Return valid JSON only."""

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

            print(f"  🌐 Calling Gemini API (gemini-2.5-flash-lite)...", file=sys.stderr, flush=True)
            api_start = datetime.now()

            # Make API request with error handling
            try:
                response = requests.post(
                    f"{gemini_url}?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json=payload_data,
                    timeout=25  # Reduced to stay under Vercel's 30s limit
                )

                print(f"  📡 API responded with status: {response.status_code}", file=sys.stderr, flush=True)

                if response.status_code != 200:
                    error_text = response.text[:500]  # Log first 500 chars of error
                    print(f"  ❌ API Error Response: {error_text}", file=sys.stderr, flush=True)
                    raise Exception(f"Gemini API error ({response.status_code}): {error_text}")

                response.raise_for_status()
                gemini_result = response.json()

            except requests.exceptions.Timeout:
                print(f"  ❌ API request timed out after 25s", file=sys.stderr, flush=True)
                raise Exception("Gemini API request timed out")
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Request failed: {str(e)}", file=sys.stderr, flush=True)
                raise Exception(f"Failed to connect to Gemini API: {str(e)}")

            api_duration = (datetime.now() - api_start).total_seconds()
            print(f"  ✓ Gemini API responded in {api_duration:.2f}s", file=sys.stderr, flush=True)

            # Parse Gemini's response
            print(f"  📊 Parsing Gemini response...", file=sys.stderr, flush=True)
            if 'candidates' in gemini_result and len(gemini_result['candidates']) > 0:
                candidate = gemini_result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    result_text = candidate['content']['parts'][0]['text'].strip()
                    print(f"  ✓ Response text length: {len(result_text)} chars", file=sys.stderr, flush=True)
                else:
                    raise Exception("Unexpected Gemini response format")
            else:
                raise Exception("No response from Gemini")

            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                print(f"  🔧 Removing markdown code blocks...", file=sys.stderr, flush=True)
                result_text = result_text.split('\n', 1)[1]
                result_text = result_text.rsplit('\n```', 1)[0]
                result_text = result_text.strip()

            print(f"  🔍 Parsing JSON response...", file=sys.stderr, flush=True)
            result_json = json.loads(result_text)

            menu_items_count = len(result_json.get('menu_items', []))
            print(f"  ✓ Parsed successfully! Found {menu_items_count} menu items", file=sys.stderr, flush=True)

            # Return successful response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response_data = {
                'original_text': result_json.get('original_text', ''),
                'translated_text': result_json.get('translated_text', ''),
                'menu_items': result_json.get('menu_items', []),
                'has_more': result_json.get('has_more', False),
                'total_dishes_estimate': result_json.get('total_dishes_estimate', len(result_json.get('menu_items', []))),
                'batch_number': batch_number,
                'detected_lang': 'zh'
            }

            self.wfile.write(json.dumps(response_data).encode())

            total_duration = (datetime.now() - start_time).total_seconds()
            print(f"  ⏱️  Total processing time: {total_duration:.2f}s", file=sys.stderr, flush=True)
            print(f"  ✅ Response sent ({len(json.dumps(response_data))} bytes)", file=sys.stderr, flush=True)

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON Parse Error: {str(e)}", file=sys.stderr, flush=True)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'JSON parse error: {str(e)}'}).encode())

        except Exception as e:
            print(f"  ❌ Error: {str(e)}", file=sys.stderr, flush=True)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
