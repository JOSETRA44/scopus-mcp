import urllib.request
import json

url = "https://api.elsevier.com/content/search/scopus?query=TITLE(%22Artificial+Intelligence%22)&count=1"
req = urllib.request.Request(url, headers={
    "X-ELS-APIKey": "3774dc7a74f2ad327a626d7ca686cd61",
    "Accept": "application/json"
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        entries = data.get("search-results", {}).get("entry", [])
        if entries:
            print("SUCCESS! Found paper:", entries[0].get("dc:title"))
        else:
            print("SUCCESS but no results")
except Exception as e:
    print("FAILED:", e)
