import sys
import argparse
import urllib.request
import json

API_KEY = "3774dc7a74f2ad327a626d7ca686cd61"

def search_scopus(query, count=5):
    url = f"https://api.elsevier.com/content/search/scopus?query={urllib.parse.quote(query)}&count={count}"
    req = urllib.request.Request(url, headers={"X-ELS-APIKey": API_KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            entries = data.get("search-results", {}).get("entry", [])
            for idx, e in enumerate(entries, 1):
                print(f"{idx}. {e.get('dc:title', 'No Title')} (ID: {e.get('dc:identifier', 'Unknown')})")
    except Exception as e:
        print("Error fetching from Scopus API:", e)

def get_abstract(scopus_id):
    if scopus_id.startswith("SCOPUS_ID:"):
        scopus_id = scopus_id.split(":")[1]
    url = f"https://api.elsevier.com/content/abstract/scopus_id/{scopus_id}"
    req = urllib.request.Request(url, headers={"X-ELS-APIKey": API_KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error fetching abstract:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scopus CLI Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    parser_search = subparsers.add_parser("search")
    parser_search.add_argument("query", help="The search query")
    parser_search.add_argument("--count", type=int, default=5)
    
    parser_abs = subparsers.add_parser("abstract")
    parser_abs.add_argument("scopus_id", help="The Scopus ID")
    
    args = parser_search.parse_args() if len(sys.argv) == 1 else parser.parse_args()
    
    if args.command == "search":
        search_scopus(args.query, args.count)
    elif args.command == "abstract":
        get_abstract(args.scopus_id)
    else:
        parser.print_help()
