import requests

url = "http://127.0.0.1:8000/ai/analyze"

with open("test.jpeg", "rb") as f:
    files = {"image": ("test.jpeg", f, "image/jpeg")}
    response = requests.post(url, files=files)

print(response.json())
