#!/usr/bin/env python3
import requests
import json

# Test the OCR endpoint
url = "http://localhost:8081/ocr"

# Example image URL with Chinese text
# Using a publicly accessible test image
test_payload = {
    "image_url": "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png"
}

print("Testing OCR API at", url)
print("Payload:", json.dumps(test_payload, indent=2))

try:
    response = requests.post(url, json=test_payload)

    if response.status_code == 200:
        result = response.json()
        print("\n✅ Success! OCR Response:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get('lines'):
            print(f"\n📝 Found {len(result['lines'])} text regions")
            print(f"🌐 Detected language: {result.get('detected_lang')}")

            # Show first few text detections
            print("\n📖 First 5 text detections:")
            for i, line in enumerate(result['lines'][:5], 1):
                print(f"  {i}. {line['text']} (confidence: {line['confidence']:.2f})")
    else:
        print(f"\n❌ Error: Status code {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to server. Make sure it's running on port 8081")
except Exception as e:
    print(f"\n❌ Error: {e}")