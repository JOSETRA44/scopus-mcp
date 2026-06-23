import urllib.request, urllib.parse, json
API_KEY = "3774dc7a74f2ad327a626d7ca686cd61"
def detail(doi):
    url = f"https://api.elsevier.com/content/abstract/doi/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(url, headers={"X-ELS-APIKey": API_KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode())
            core = data.get("abstracts-retrieval-response", {})
            head = core.get("item", {}).get("bibrecord", {}).get("head", {})
            coredata = core.get("coredata", {})
            title = coredata.get("dc:title","-")
            pub = coredata.get("prism:publicationName","-")
            vol = coredata.get("prism:volume","-")
            issue = coredata.get("prism:issueIdentifier","-")
            pages = coredata.get("prism:pageRange","-")
            year = coredata.get("prism:coverDate","-")
            abstract = coredata.get("dc:description","-")
            # authors
            authors = []
            authgroup = core.get("authors", {}).get("author", [])
            if isinstance(authgroup, dict): authgroup=[authgroup]
            for a in authgroup:
                authors.append(f"{a.get('ce:surname','')}, {a.get('ce:initials','')}")
            print(f"\n##### DOI {doi}")
            print("TITLE:", title)
            print("AUTHORS:", "; ".join(authors))
            print(f"PUB: {pub} | vol {vol} | issue {issue} | pp {pages} | {year}")
            print("ABSTRACT:", (abstract or '-')[:900])
    except Exception as ex:
        print("ERR", doi, ex)

for d in [
 "10.1016/j.japwor.2026.101357",
 "10.1080/09645292.2024.2354848",
 "10.1016/j.labeco.2024.102505",
 "10.15691/07194714.2024.004",
 "10.1177/01678329251340465",
 "10.1177/09504222261423341",
]:
    detail(d)
