# Deploy Flask App to Railway - Quick Guide

## Step 1: Prepare Your App
1. Make sure you have these files in your repo:
   - `requirements.txt` ✅ (you already have this)
   - `app.py` ✅ (you already have this)

## Step 2: Create Procfile
Create a file named `Procfile` (no extension) with:
```
web: python app.py
```

## Step 3: Update app.py for Railway
Add this to the bottom of your app.py:
```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=False, host='0.0.0.0', port=port)
```

## Step 4: Deploy to Railway
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your River repository
5. Railway will automatically detect it's a Python app and deploy!

## Step 5: Environment Variables
In Railway dashboard, add your environment variables:
- `SECRET_KEY`
- `GOOGLE_API_KEY`
- `SETU_CLIENT_ID`
- `SETU_CLIENT_SECRET`
- etc.

## Benefits of Railway:
- ✅ No serverless conversion needed
- ✅ Real Flask app deployment
- ✅ Built-in database options
- ✅ Automatic HTTPS
- ✅ GitHub integration
- ✅ $5/month free credit (usually enough)