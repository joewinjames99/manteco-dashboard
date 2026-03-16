# Manteco Price Resilience Dashboard

## Deploy to Railway
1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Set environment variables:
   - ANTHROPIC_API_KEY = your key
   - SECRET_KEY = any password your team will use
4. Done — Railway gives you a live URL

## Environment Variables
| Variable | Description |
|---|---|
| ANTHROPIC_API_KEY | For scraping (optional) |
| SECRET_KEY | Team password for saving data |
| DATA_PATH | Where to store data (default: data/manteco_data.json) |

## Local development
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
export SECRET_KEY="yourpassword"
python server.py
```
