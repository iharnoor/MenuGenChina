#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import base64
from urllib.parse import urlparse, parse_qs

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

            # Mock OCR response
            response = {
                'success': True,
                'text': """Sample Menu Items:
Spring Rolls - $8.99
Crispy vegetable rolls served with sweet chili sauce

Beef Noodle Soup - $12.99
Traditional beef broth with tender beef and rice noodles

Kung Pao Chicken - $14.99
Spicy chicken with peanuts and vegetables

Fried Rice - $10.99
Wok-fried rice with egg and mixed vegetables

Green Tea Ice Cream - $5.99
Homemade green tea flavored ice cream""",
                'language': 'en'
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif self.path == '/translate':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            # Mock translation
            text = data.get('text', '')
            target_lang = data.get('target', 'es')

            # Simple mock translations
            translations = {
                'es': 'Texto traducido al español: ' + text[:50] + '...',
                'fr': 'Texte traduit en français: ' + text[:50] + '...',
                'de': 'Ins Deutsche übersetzter Text: ' + text[:50] + '...',
                'zh': '翻译成中文的文本: ' + text[:50] + '...'
            }

            response = {
                'success': True,
                'translatedText': translations.get(target_lang, f'Translated to {target_lang}: {text}')
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8081), OCRHandler)
    print('OCR Server running on port 8081...')
    server.serve_forever()