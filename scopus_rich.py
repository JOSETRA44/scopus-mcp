import urllib.request, urllib.parse, json, sys
API_KEY = "3774dc7a74f2ad327a626d7ca686cd61"
def search(query, count=8):
    url = f"https://api.elsevier.com/content/search/scopus?query={urllib.parse.quote(query)}&count={count}"
    req = urllib.request.Request(url, headers={"X-ELS-APIKey": API_KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
            entries = data.get("search-results", {}).get("entry", [])
            print(f"\n===== QUERY: {query} =====")
            for i, e in enumerate(entries, 1):
                title = e.get("dc:title","-")
                creator = e.get("dc:creator","-")
                pub = e.get("prism:publicationName","-")
                year = e.get("prism:coverDate","-")
                doi = e.get("prism:doi","-")
                cites = e.get("citedby-count","-")
                print(f"{i}. {creator} | {title}")
                print(f"   {pub} ({year}) | DOI: {doi} | cited: {cites}")
    except Exception as ex:
        print("ERR", query, ex)

queries = [
  'TITLE-ABS-KEY("skill mismatch" AND "higher education" AND employability)',
  'TITLE-ABS-KEY("returns to education" AND quality AND university)',
  'TITLE-ABS-KEY("reservation wage" AND students AND expectations)',
  'TITLE-ABS-KEY("digital divide" AND "higher education" AND "Latin America")',
  'TITLE-ABS-KEY("educational resources" AND employability AND university)',
  'TITLE-ABS-KEY("human capital" AND "graduate employability" AND Peru)',
]
for q in queries:
    search(q, 6)
