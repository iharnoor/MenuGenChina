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

            # Get OpenAI API key from environment
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                print(f"  ❌ Error: OPENAI_API_KEY not configured", file=sys.stderr, flush=True)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'OPENAI_API_KEY not configured'}).encode())
                return

            # Get image data
            print(f"  🖼️  Decoding image data...", file=sys.stderr, flush=True)
            image_data = payload.get('image', '')
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            print(f"  ✓ Image decoded ({len(image_bytes)} bytes)", file=sys.stderr, flush=True)

            # Prepare OpenAI API request
            openai_url = "https://api.openai.com/v1/chat/completions"

            target_lang = payload.get('target_lang', 'en')

            # Load system prompt from SystemPrompt.txt
            system_prompt = load_system_prompt()

            # Combine with JSON structure for one comprehensive API call
            prompt = f"""{system_prompt}

Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
  "original_text": "all Chinese text from the menu, separated by newlines",
  "translated_text": "full English translation, preserving structure",
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
  ]
}}

Provide ALL requested information for EVERY dish in ONE response. Return valid JSON only."""

            payload_data = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096
            }

            print(f"  🌐 Calling OpenAI API (gpt-4o)...", file=sys.stderr, flush=True)
            api_start = datetime.now()

            # Make API request
            response = requests.post(
                openai_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=payload_data,
                timeout=60
            )
            response.raise_for_status()
            openai_result = response.json()

            api_duration = (datetime.now() - api_start).total_seconds()
            print(f"  ✓ OpenAI API responded in {api_duration:.2f}s", file=sys.stderr, flush=True)

            # Parse OpenAI's response
            print(f"  📊 Parsing OpenAI response...", file=sys.stderr, flush=True)
            if 'choices' in openai_result and len(openai_result['choices']) > 0:
                choice = openai_result['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    result_text = choice['message']['content'].strip()
                    print(f"  ✓ Response text length: {len(result_text)} chars", file=sys.stderr, flush=True)
                else:
                    raise Exception("Unexpected OpenAI response format")
            else:
                raise Exception("No response from OpenAI")

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
