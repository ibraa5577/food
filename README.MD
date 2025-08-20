## How to use
1. Run the API service: uvicorn `src.main:app --host 0.0.0.0 --port 8000 --reload`
2. Tunnel it (Use a new terminal window): `cloudflared tunnel --url http://127.0.0.1:8000`
3. Use the API base given by CloudFlare + Endpoint (Main endpoint "/process-image" )
4. Use POST method to upload an image


### Example with python:
```python
import requests

url = "https://obligation-boundaries-passenger-performing.trycloudflare.com/process-image"
files = {"file": open("1.jpg", "rb")}
response = requests.post(url, files=files)
print(response.text)
print(response.json())```
