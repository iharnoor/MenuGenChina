# OCR Service (Phase 1)

A minimal FastAPI service to perform OCR on menu images, detect language, and return structured text lines with bounding boxes and confidences. Pluggable providers:

- Google Cloud Vision (preferred if credentials provided)
- PaddleOCR (CPU) fallback

## Quick Start

### 1) Configure environment

Create `.env` (optional):

```
# OCR provider selection: vision | paddle
OCR_PROVIDER=vision

# Google Cloud credentials (only needed if using vision)
GOOGLE_APPLICATION_CREDENTIALS=/app/creds/gcp.json

# Translation: google | none
TRANSLATE_PROVIDER=google
GOOGLE_PROJECT_ID=your-gcp-project
```

Place your GCP service account json at `services/ocr/creds/gcp.json` or mount it at runtime.

### 2) Run with Docker

Build:

```
docker build -t menugen-ocr:latest .
```

Run (Vision):

```
docker run --rm -p 8081:8081 \
  -e OCR_PROVIDER=vision \
  -e TRANSLATE_PROVIDER=google \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/creds/gcp.json \
  -v $(pwd)/creds:/app/creds:ro \
  menugen-ocr:latest
```

Run (PaddleOCR):

```
docker run --rm -p 8081:8081 \
  -e OCR_PROVIDER=paddle \
  -e TRANSLATE_PROVIDER=none \
  menugen-ocr:latest
```

### 3) Call the API

```
curl -s -X POST http://localhost:8081/ocr \
  -H 'Content-Type: application/json' \
  -d '{"image_url":"https://example.com/menu.jpg","target_lang":"en"}' | jq .
```

Response:

```
{
  "detected_lang": "zh-cn",
  "lines": [
    {"text":"红烧肉","confidence":0.97,"box":[[0,0],[10,0],[10,10],[0,10]],"translated":"Red braised pork"}
  ]
}
```

## Dev (without Docker)

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

Note: PaddleOCR may require system packages (libgl). Prefer Docker for consistency.

## Files

- `app/main.py` FastAPI app and routes
- `app/ocr.py` OCR provider interfaces and implementations
- `app/models.py` Pydantic models
- `Dockerfile` Runtime image
- `requirements.txt` Python deps

