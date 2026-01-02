# Deployment Guide - Voice Conversational Kids Game

This guide will help you deploy your voice game to production using Railway (backend) and Vercel (frontend).

## Architecture Overview

- **Frontend**: React app hosted on Vercel (free tier)
- **Backend**: FastAPI + Ollama on Railway ($5-10/month)
- **APIs**: ElevenLabs for STT and TTS (cloud-based)

---

## Prerequisites

Before deploying, make sure you have:

1. ✅ GitHub account
2. ✅ Railway account (sign up at https://railway.app)
3. ✅ Vercel account (sign up at https://vercel.com)
4. ✅ ElevenLabs API key (from your .env file)
5. ✅ Git installed locally

---

## Part 1: Deploy Backend to Railway

### Step 1: Push Code to GitHub

```bash
# Initialize git repository (if not already done)
cd voice-game
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for deployment"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/voice-game.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Railway

1. Go to https://railway.app and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `voice-game` repository
5. Railway will auto-detect the `Dockerfile` in `voice_service/`

### Step 3: Configure Railway

1. In Railway dashboard, click on your service
2. Go to **"Settings"** → **"Root Directory"**
   - Set to: `voice_service`
3. Go to **"Variables"** tab and add:
   ```
   ELEVENLABS_API_KEY=sk_8a9dab925a2b6273f5d1bc4e31bc95b053e6396ce6022a75
   ELEVENLABS_VOICE=tapn1QwocNXk3viVSowa
   ELEVENLABS_MODEL=eleven_monolingual_v1
   ELEVENLABS_STT_MODEL=scribe_v1
   PORT=8008
   ```

4. Go to **"Settings"** → **"Networking"**
   - Click **"Generate Domain"** to get a public URL
   - Copy this URL (e.g., `https://your-app-name.up.railway.app`)

### Step 4: Verify Backend Deployment

Wait 5-10 minutes for:
- Container to build
- Ollama to install
- Model to download (qwen2.5:0.5b-instruct)

Check logs in Railway dashboard. You should see:
```
Starting Ollama service...
Pulling Ollama model...
Starting FastAPI server...
Uvicorn running on http://0.0.0.0:8008
```

Test the health endpoint:
```bash
curl https://your-app-name.up.railway.app/health
```

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Update Production Environment

Edit `web-client/.env.production`:

```env
# Replace with your Railway backend URL
VITE_API_BASE_URL=https://your-app-name.up.railway.app
VITE_WS_BASE_URL=wss://your-app-name.up.railway.app
```

Commit the change:
```bash
git add web-client/.env.production
git commit -m "Update production API URL"
git push
```

### Step 2: Deploy to Vercel

1. Go to https://vercel.com and sign in
2. Click **"Add New Project"**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `web-client`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Click **"Deploy"**

### Step 3: Verify Frontend Deployment

After deployment completes:
1. Vercel will give you a URL (e.g., `https://voice-game.vercel.app`)
2. Open it in your browser
3. Click the "Talk" button and test voice interaction

---

## Part 3: Configure CORS (Backend)

Your backend needs to allow requests from your Vercel frontend.

1. Go to Railway dashboard
2. Add environment variable:
   ```
   CORS_ORIGINS=https://voice-game.vercel.app,https://voice-game-*.vercel.app
   ```
   (Replace with your actual Vercel domain)
3. Redeploy if needed

---

## Cost Estimate

### Monthly Costs:

- **Railway**: ~$5-10/month
  - Starts at $5 for 512MB RAM
  - Recommend 2GB RAM for Ollama: ~$10/month

- **Vercel**: $0 (free tier)
  - 100GB bandwidth/month
  - Unlimited requests

- **ElevenLabs**: Pay-per-use
  - ~$0.001-0.003 per request
  - Free tier: 10,000 characters/month

**Total**: ~$10-15/month for moderate usage

---

## Monitoring & Troubleshooting

### Railway Logs

View real-time logs:
1. Go to Railway dashboard
2. Click on your service
3. Go to **"Deployments"** → Click latest deployment
4. View **"Logs"** tab

### Common Issues

**Issue: Ollama model not loading**
- Check logs for "Pulling Ollama model..."
- Railway might need more RAM (upgrade to 2GB plan)

**Issue: Frontend can't connect to backend**
- Verify CORS_ORIGINS includes your Vercel domain
- Check Railway service is running (green status)
- Test backend health endpoint

**Issue: WebSocket connection fails**
- Railway supports WebSockets by default
- Check VITE_WS_BASE_URL uses `wss://` (not `ws://`)

**Issue: High latency**
- Ollama on Railway can be slow on small instances
- Consider upgrading RAM or switching to cloud LLM (OpenAI/Claude)

---

## Scaling Options

### If you get more users:

**Option 1: Upgrade Railway**
- Increase RAM to 4GB or 8GB
- Better Ollama performance

**Option 2: Replace Ollama with Cloud LLM**
- Switch to OpenAI API or Anthropic Claude
- Much faster, scales automatically
- ~$0.01-0.03 per conversation

**Option 3: Multi-region Deployment**
- Deploy to multiple Railway regions
- Use Vercel's edge network (automatic)

---

## Security Checklist

- ✅ API keys in Railway environment variables (not in code)
- ✅ CORS configured for your domain only
- ✅ HTTPS enabled (automatic on Railway & Vercel)
- ✅ WebSocket over WSS (secure)
- ✅ No sensitive data in frontend code

---

## Updating the Application

### Update Backend:
```bash
git add voice_service/
git commit -m "Update backend"
git push
```
Railway will auto-deploy.

### Update Frontend:
```bash
git add web-client/
git commit -m "Update frontend"
git push
```
Vercel will auto-deploy.

---

## Rollback

### Railway:
1. Go to **"Deployments"**
2. Find previous successful deployment
3. Click **"Redeploy"**

### Vercel:
1. Go to **"Deployments"**
2. Find previous deployment
3. Click **"Promote to Production"**

---

## Support

- Railway Docs: https://docs.railway.app
- Vercel Docs: https://vercel.com/docs
- ElevenLabs Docs: https://elevenlabs.io/docs

---

## Next Steps

After successful deployment:

1. **Test thoroughly**: Test voice interactions, math questions, conversation memory
2. **Monitor usage**: Check Railway metrics and ElevenLabs usage
3. **Set up alerts**: Configure Railway to notify you of downtime
4. **Share with users**: Your app is now live! 🎉

Deployed URLs:
- Frontend: `https://your-app.vercel.app`
- Backend: `https://your-app-name.up.railway.app`
- Health Check: `https://your-app-name.up.railway.app/health`
