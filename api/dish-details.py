import os
import json
from http.server import BaseHTTPRequestHandler
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

            chinese_name = payload.get('chinese_name', '')
            english_name = payload.get('english_name', '')

            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

            prompt = f"""Provide details about this Chinese dish:
Chinese: {chinese_name}
English: {english_name}

Return ONLY valid JSON (no markdown):
{{
  "cultural_details": "brief background (1-2 sentences)",
  "ingredients": ["main", "ingredients"],
  "spiciness_level": "none/mild/medium/hot/very hot",
  "dietary_info": ["vegetarian", "vegan", "halal", "gluten-free", etc.],
  "regional_origin": "province/region",
  "recommended_pairings": ["pairings"],
  "nutritional_info": "brief overview"
}}

Be concise. Return valid JSON only."""

            payload_data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }

            # Make API request with timeout
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
            self.wfile.write(json.dumps(result_json).encode())

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
