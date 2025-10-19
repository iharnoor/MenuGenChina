import os
import json
import base64
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import requests

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            # Get Gemini API key from environment
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'GEMINI_API_KEY not configured'}).encode())
                return

            # Get image data
            image_data = payload.get('image', '')
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Prepare Gemini API request with optimized prompt for speed
            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

            target_lang = payload.get('target_lang', 'en')

            prompt = f"""Extract text from this Chinese menu and translate to {target_lang}.

SPEED IS CRITICAL - keep it simple and fast.

Return ONLY valid JSON (no markdown):
{{
  "original_text": "all Chinese text, separated by newlines",
  "translated_text": "the translation, preserving structure",
  "menu_items": [
    {{
      "chinese": "dish name in Chinese",
      "english": "dish name in {target_lang}",
      "price": "price if visible"
    }}
  ]
}}

BE FAST - extract basics only. No cultural details, no pinyin needed."""

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
            response = requests.post(
                f"{gemini_url}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload_data,
                timeout=9
            )
            response.raise_for_status()
            gemini_result = response.json()

            # Parse Gemini's response
            if 'candidates' in gemini_result and len(gemini_result['candidates']) > 0:
                candidate = gemini_result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    result_text = candidate['content']['parts'][0]['text'].strip()
                else:
                    raise Exception("Unexpected Gemini response format")
            else:
                raise Exception("No response from Gemini")

            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('\n', 1)[1]
                result_text = result_text.rsplit('\n```', 1)[0]
                result_text = result_text.strip()

            result_json = json.loads(result_text)

            # Return successful response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response_data = {
                'original_text': result_json.get('original_text', ''),
                'translated_text': result_json.get('translated_text', ''),
                'menu_items': result_json.get('menu_items', []),
                'detected_lang': 'zh'
            }

            self.wfile.write(json.dumps(response_data).encode())

        except json.JSONDecodeError as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'JSON parse error: {str(e)}'}).encode())

        except Exception as e:
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
