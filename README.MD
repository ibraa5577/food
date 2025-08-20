## How to use
1 - uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
2 - (New Terminal) cloudflared tunnel --url http://127.0.0.1:8000
3 - Use the API base given by CloudFlare + Endpoint (Main endpoint "/process-image" )
4 - Use POST to upload an image
### Example:
```import requests
url = "https://obligation-boundaries-passenger-performing.trycloudflare.com/process-image"
files = {"file": open("1.jpg", "rb")}
response = requests.post(url, files=files)
print(response.text)
print(response.json())```

## Remaining To-Do's
- [ ] Cleaning unnecessary comments/lines (e.g. ADI and other removed tools)
- [ ] Allergens .csv and its function
- [ ] Delete main.ipynb
- [ ] Transferring other confidentials (API keys, emails, etc..) to app_config.py/.env
- [X] Fixing Research Papers tool returning unreleveant papers
- [ ] No More?
