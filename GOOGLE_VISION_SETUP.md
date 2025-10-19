# Google Cloud Vision API Setup Guide

## Quick Setup (5 minutes)

### 1. Get Google Cloud Account
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Sign in with your Google account
- New users get $300 free credits (enough for ~200,000 OCR requests!)

### 2. Create a Project
1. Click "Select a project" → "New Project"
2. Name it "menu-translator"
3. Click "Create"

### 3. Enable Vision API
1. Go to [Vision API Page](https://console.cloud.google.com/apis/library/vision.googleapis.com)
2. Click "Enable"

### 4. Create API Key
1. Go to [Credentials Page](https://console.cloud.google.com/apis/credentials)
2. Click "+ CREATE CREDENTIALS" → "API Key"
3. Copy the API key

### 5. (Optional) Restrict API Key
1. Click on your API key
2. Under "API restrictions" → "Restrict key"
3. Select "Cloud Vision API" and "Cloud Translation API"
4. Save

## Local Testing

```bash
# Set API key as environment variable
export GOOGLE_VISION_API_KEY="your-api-key-here"

# Run the server
python3 ocr_server_google.py
```

## For Production (Vercel)

Add to your Vercel environment variables:
```
GOOGLE_VISION_API_KEY=your-api-key-here
```

## Pricing
- First 1000 images/month: **FREE**
- After that: $1.50 per 1000 images
- With $300 credit: ~200,000 free images!

## Test Your Setup

Once server is running, the app will automatically use Google Vision for OCR:
1. Open `index.html` in browser
2. Upload a Chinese menu image
3. You should see actual Chinese text extracted!

## Troubleshooting

If OCR isn't working:
1. Check console for API key message
2. Verify API is enabled in Google Cloud Console
3. Check API key permissions
4. Look for error messages in server console

## No API Key?

The server will still work with mock data for testing - just run without setting the API key.