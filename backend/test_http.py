import urllib.request
import urllib.error
import json

url = "http://localhost:8000/api/repos/5118615f-bcf5-48c8-aebc-47d59b5999b2/project-brain"
req = urllib.request.Request(url)
# Add dummy auth cookie if needed
# req.add_header("Cookie", "devbrain_session=something")

try:
    response = urllib.request.urlopen(req)
    print("STATUS:", response.status)
    print(response.read().decode('utf-8')[:200])
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print(e.read().decode('utf-8'))
except urllib.error.URLError as e:
    print("URL ERROR:", e.reason)
