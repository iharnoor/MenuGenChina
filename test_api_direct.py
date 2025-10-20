#!/usr/bin/env python3
"""
Direct test of the API with full logging
"""
import os
import sys
import base64
from pathlib import Path

# Set unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    print("✓ Loaded .env file\n")

# Import our API handler
sys.path.insert(0, str(Path(__file__).parent / "api"))

print("="*60)
print("Testing Menu API Directly")
print("="*60 + "\n")

# Load test image
image_path = Path(__file__).parent / "chinese menu test.jpg"
print(f"📁 Loading test image: {image_path.name}")
with open(image_path, 'rb') as f:
    image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    image_data = f"data:image/jpeg;base64,{image_base64}"
print(f"✓ Image loaded ({len(image_bytes)} bytes)\n")

# Create a mock request
import json
payload = {
    'image': image_data,
    'target_lang': 'en'
}

print("="*60)
print("Calling API Handler...")
print("="*60 + "\n")

# Mock the handler parts
class MockRequest:
    def __init__(self, body):
        self.body = body
        self._position = 0

    def read(self, size):
        result = self.body[self._position:self._position + size]
        self._position += size
        return result

class MockWFile:
    def __init__(self):
        self.data = b''

    def write(self, data):
        self.data += data

class MockHandler:
    def __init__(self, payload_json):
        self.headers = {'Content-Length': str(len(payload_json))}
        self.rfile = MockRequest(payload_json)
        self.wfile = MockWFile()
        self.response_code = None
        self.response_headers = {}

    def send_response(self, code):
        self.response_code = code
        print(f"\n{'='*60}")
        print(f"Response Code: {code}")
        print(f"{'='*60}\n")

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

# Create handler and call it
from menu import handler as MenuHandler

payload_json = json.dumps(payload).encode('utf-8')
mock = MockHandler(payload_json)

# Manually create handler and call do_POST
h = MenuHandler(None, None, None)
h.headers = mock.headers
h.rfile = mock.rfile
h.wfile = mock.wfile
h.send_response = mock.send_response
h.send_header = mock.send_header
h.end_headers = mock.end_headers

# Call the API
h.do_POST()

# Print results
if mock.response_code == 200:
    response_data = json.loads(mock.wfile.data.decode('utf-8'))
    menu_items = response_data.get('menu_items', [])

    print("\n" + "="*60)
    print(f"✅ SUCCESS! Found {len(menu_items)} menu items")
    print("="*60 + "\n")

    for i, item in enumerate(menu_items[:3], 1):
        print(f"--- Dish {i} ---")
        print(f"Chinese: {item.get('chinese', 'N/A')}")
        print(f"English: {item.get('english', 'N/A')}")
        print(f"Spice: {item.get('spiciness_level', 'N/A')}")
        print(f"Pork: {item.get('pork_alert', 'N/A')}")
        print()

    if len(menu_items) > 3:
        print(f"... and {len(menu_items) - 3} more items")
else:
    print(f"\n❌ Error: {mock.wfile.data.decode('utf-8')}")
