#!/usr/bin/env python3
"""
OCR Server using Google Cloud Vision API
Designed for Vercel deployment compatibility
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import base64
import os
from urllib.parse import urlparse
import hashlib
import requests
from datetime import datetime

# Simple in-memory cache (in production, use Redis/KV)
ocr_cache = {}

class OCRHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/ocr':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            try:
                # Get base64 image from request
                image_data = data.get('image', '')

                # Remove data URL prefix if present
                if ',' in image_data:
                    image_data = image_data.split(',')[1]

                # Create cache key from image hash
                image_hash = hashlib.md5(image_data.encode()).hexdigest()

                # Check cache first
                if image_hash in ocr_cache:
                    print(f"Cache hit for image {image_hash}")
                    cached_result = ocr_cache[image_hash]
                    self.send_success_response(cached_result)
                    return

                # Prepare request for Google Vision API
                api_key = os.environ.get('GOOGLE_VISION_API_KEY')

                if not api_key:
                    # Fallback to mock data if no API key
                    print("Warning: No Google Vision API key found, using mock data")
                    mock_result = self.get_mock_chinese_menu_data()
                    self.send_success_response(mock_result)
                    return

                # Call Google Vision API
                vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

                vision_request = {
                    "requests": [{
                        "image": {
                            "content": image_data
                        },
                        "features": [{
                            "type": "TEXT_DETECTION",
                            "maxResults": 1
                        }],
                        "imageContext": {
                            "languageHints": ["zh", "en"]  # Hint for Chinese and English
                        }
                    }]
                }

                response = requests.post(vision_url, json=vision_request)

                if response.status_code == 200:
                    vision_data = response.json()

                    if 'responses' in vision_data and vision_data['responses']:
                        text_annotations = vision_data['responses'][0].get('textAnnotations', [])

                        if text_annotations:
                            extracted_text = text_annotations[0]['description']

                            result = {
                                'success': True,
                                'text': extracted_text,
                                'language': 'zh',  # Detected Chinese
                                'source': 'google_vision',
                                'timestamp': datetime.now().isoformat()
                            }

                            # Cache the result
                            ocr_cache[image_hash] = result

                            self.send_success_response(result)
                        else:
                            self.send_error_response("No text found in image")
                    else:
                        self.send_error_response("Invalid response from Vision API")
                else:
                    print(f"Vision API error: {response.status_code} - {response.text}")
                    # Fallback to mock data on API error
                    mock_result = self.get_mock_chinese_menu_data()
                    self.send_success_response(mock_result)

            except Exception as e:
                print(f"Error processing OCR: {e}")
                self.send_error_response(str(e))

        elif self.path == '/translate':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            text = data.get('text', '')
            target_lang = data.get('target', 'en')

            try:
                # Try Google Translate API
                api_key = os.environ.get('GOOGLE_TRANSLATE_API_KEY') or os.environ.get('GOOGLE_VISION_API_KEY')

                if api_key:
                    translate_url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"

                    translate_request = {
                        'q': text,
                        'target': target_lang,
                        'source': 'auto'
                    }

                    response = requests.post(translate_url, json=translate_request)

                    if response.status_code == 200:
                        translate_data = response.json()
                        translated_text = translate_data['data']['translations'][0]['translatedText']

                        result = {
                            'success': True,
                            'translatedText': translated_text,
                            'source': 'google_translate'
                        }

                        self.send_success_response(result)
                        return

                # Fallback to mock translation
                mock_translation = self.get_mock_translation(text, target_lang)
                self.send_success_response(mock_translation)

            except Exception as e:
                print(f"Translation error: {e}")
                mock_translation = self.get_mock_translation(text, target_lang)
                self.send_success_response(mock_translation)

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_response(self, message):
        response = {
            'success': False,
            'error': message
        }
        self.send_response(500)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def get_mock_chinese_menu_data(self):
        """Return realistic Chinese menu data for testing"""
        return {
            'success': True,
            'text': """凉菜
花生豆腐汤 ——— 8元
鱼香肉丝套餐 ——— 8元
宫保鸡丁套餐 ——— 8元

汤类
花蛤豆腐汤 ——— 8元
鱼头豆腐汤 ——— 12元
干贝冬瓜汤 ——— 15元
七彩牛肉羹 ——— 15元

热菜粥粉
海鲜粥 ——— 8元
香滑田鸡粥 ——— 8元
鸡汁汤面 ——— 5元
排骨面 ——— 6元
海鲜汤面 ——— 7元
海鲜米粉汤 ——— 7元
特色卤面 ——— 8元
海鲜乌冬面 ——— 8元

单品菜
川味回锅肉 ——— 10元
梦城茄枝肉 ——— 10元
鱼香肉丝 ——— 10元
青椒炒肉丝 ——— 10元
剁椒鱼头 ——— 20元""",
            'language': 'zh',
            'source': 'mock_data',
            'timestamp': datetime.now().isoformat()
        }

    def get_mock_translation(self, text, target_lang):
        """Return mock translation for testing"""
        # Simple mock translation - just prepend language indicator
        translations = {
            'en': f"[English Translation] {text[:100]}...",
            'es': f"[Spanish Translation] {text[:100]}...",
            'fr': f"[French Translation] {text[:100]}...",
            'de': f"[German Translation] {text[:100]}...",
        }

        return {
            'success': True,
            'translatedText': translations.get(target_lang, f"[{target_lang} Translation] {text[:100]}..."),
            'source': 'mock'
        }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))

    # Check for API key
    if not os.environ.get('GOOGLE_VISION_API_KEY'):
        print("\n" + "="*60)
        print("WARNING: No Google Vision API key found!")
        print("Running with mock data only.")
        print("To use Google Vision, set GOOGLE_VISION_API_KEY environment variable")
        print("="*60 + "\n")
    else:
        print(f"Google Vision API key found: {os.environ.get('GOOGLE_VISION_API_KEY')[:10]}...")

    server = HTTPServer(('0.0.0.0', port), OCRHandler)
    print(f'OCR Server running on port {port}...')
    print(f'Test at: http://localhost:{port}/ocr')
    server.serve_forever()