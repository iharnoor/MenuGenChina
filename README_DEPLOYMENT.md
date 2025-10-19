# MenuGenChina - Vercel Deployment Guide

## 🚀 Deploy to Vercel (Serverless)

### Prerequisites
1. A [Vercel account](https://vercel.com/signup) (free tier works!)
2. A [Gemini API key](https://makersuite.google.com/app/apikey)

### Deployment Steps

#### Option 1: Deploy via GitHub (Recommended)

1. **Push your code to GitHub**
   ```bash
   git push origin main
   ```

2. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository `MenuGenChina`

3. **Configure Environment Variables**
   - In the Vercel project settings, go to "Environment Variables"
   - Add the following:
     - **Name**: `GEMINI_API_KEY`
     - **Value**: Your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Click "Add"

4. **Deploy**
   - Click "Deploy"
   - Wait ~1-2 minutes for build to complete
   - Your app will be live at `https://your-project-name.vercel.app`

#### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Set Environment Variable**
   ```bash
   vercel env add GEMINI_API_KEY
   ```
   Then paste your Gemini API key when prompted.

4. **Deploy**
   ```bash
   vercel --prod
   ```

### 🎯 How It Works (Serverless Architecture)

#### API Endpoints
- **`/api/ocr`** - Extracts text and menu items from image (7-10s, under free tier limit)
- **`/api/dish-details`** - Gets detailed info for a specific dish on-demand (3-5s per dish)

#### Free Tier Optimizations
1. **Image compression**: Reduced to 600px width, 70% quality
2. **Fast initial load**: OCR only extracts basics (no pinyin, no details)
3. **On-demand details**: User clicks "Show Details" button to load rich info
4. **All under 10s timeout**: Each serverless function completes in <10 seconds

### 📊 Performance

| Metric | Time |
|--------|------|
| Initial OCR (text + menu items) | 7-10s |
| Per-dish details (on-demand) | 3-5s |
| **Total under free tier limits** | ✅ Yes |

### 🔧 Local Testing

To test the serverless functions locally:

```bash
# Install Vercel CLI
npm install -g vercel

# Run local dev server
vercel dev
```

Then open `http://localhost:3000` in your browser.

**Note**: You'll need to create a `.env` file with your `GEMINI_API_KEY` for local testing:
```bash
cp .env.example .env
# Edit .env and add your API key
```

### 🌐 Custom Domain (Optional)

After deployment, you can add a custom domain:
1. Go to your Vercel project settings
2. Navigate to "Domains"
3. Add your custom domain
4. Follow the DNS configuration instructions

### 🐛 Troubleshooting

**"GEMINI_API_KEY not configured" error**
- Make sure you added the environment variable in Vercel dashboard
- Redeploy after adding env vars

**Timeout errors**
- Check if your Gemini API key is valid
- Ensure images aren't too large (app auto-compresses to 600px)

**CORS errors**
- Should not happen - CORS headers are configured in serverless functions
- If you see this, check browser console for details

### 📝 Project Structure

```
MenuGenChina/
├── index.html           # Frontend (static)
├── api/
│   ├── ocr.py          # Serverless function: OCR endpoint
│   └── dish-details.py # Serverless function: dish details endpoint
├── vercel.json         # Vercel configuration
├── requirements.txt    # Python dependencies
└── README_DEPLOYMENT.md # This file
```

### 💡 Tips

1. **Monitor usage**: Check Vercel dashboard for function invocations
2. **Optimize images**: Smaller images = faster processing
3. **Cache results**: Consider browser localStorage for frequently viewed dishes
4. **Upgrade if needed**: If you need longer timeouts, upgrade to Vercel Pro ($20/mo)

---

**Questions?** Check the [Vercel docs](https://vercel.com/docs) or open an issue on GitHub.
