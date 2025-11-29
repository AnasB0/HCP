# HCP - AI-Powered Healthcare Platform

## Local Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run training: `python train_models.py`
3. Start app: `streamlit run main.py`

## Deploy to Streamlit Cloud
1. Push to GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → GitHub → your repo → Select `main.py` → Deploy

## Secrets (Required for AI features)
In Streamlit Cloud, add to Advanced Settings → Secrets:
```
OPENROUTER_API_KEY = "your_openrouter_api_key_here"
```

## Notes
- SQLite DB resets on restart (demo only)
- Models included as joblib files
- File uploads not persistent