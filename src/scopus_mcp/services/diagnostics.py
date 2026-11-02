"""Endpoint-specific diagnostics. Probe results never infer other entitlements."""
from datetime import datetime, timezone

from ..client import ScopusClient
from ..exceptions import ScopusAPIError, ScopusAuthError, ScopusRateLimitError, ScopusNetworkError
from ..formatters import (format_search_results, format_abstract, format_author_profile,
                          format_author_search_results, format_affiliation_search_results,
                          format_citation_count, format_citations_overview)


async def diagnose(client: ScopusClient) -> dict:
    year = datetime.now(timezone.utc).year
    probes = {
        "search": ("/content/search/scopus", {"query": "TITLE(test)", "count": 1}, "search-results"),
        "abstract": ("/content/abstract/scopus_id/85180904906", {"view": "FULL"}, "abstracts-retrieval-response"),
        "author": ("/content/author/author_id/7401234567", {"view": "ENHANCED"}, "author-retrieval-response"),
        "search-authors": ("/content/search/author", {"query": "AUTHLASTNAME(Smith)", "count": 1}, "search-results"),
        "search-affiliations": ("/content/search/affiliation", {"query": "AFFIL(MIT)", "count": 1}, "search-results"),
        "citation-count": ("/content/abstract/citation-count", {"scopus_id": "85180904906"}, "abstract-citations-response"),
        "citations": ("/content/abstract/citations", {"scopus_id": "85180904906", "date": f"{year-1}-{year}"}, "abstract-citations-response"),
    }
    capabilities = {}
    validators = {"search": format_search_results, "abstract": format_abstract,
                  "author": format_author_profile, "search-authors": format_author_search_results,
                  "search-affiliations": format_affiliation_search_results,
                  "citation-count": format_citation_count, "citations": format_citations_overview}
    for name, (path, params, root) in probes.items():
        try:
            response = await client.request(path, params=params)
            payload = response.get(root)
            if not payload or (isinstance(payload, dict) and any(k in payload for k in ("error", "error-response", "service-error"))):
                raise ScopusAPIError("Missing or invalid diagnostic payload")
            validators[name](response)
            capabilities[name] = "ok"
        except ScopusAuthError as exc:
            capabilities[name] = "unauthorized: verify API key and network" if exc.status_code == 401 else "forbidden: verify endpoint entitlement and institutional access"
        except ScopusRateLimitError:
            capabilities[name] = "rate limited; access not verified"
        except ScopusNetworkError:
            capabilities[name] = "network error; access not verified"
        except (ValueError, TypeError, KeyError):
            capabilities[name] = "unexpected response; access not verified"
        except ScopusAPIError as exc:
            capabilities[name] = f"API error ({exc.status_code or 'invalid response'}); access not verified"
    return {"capabilities": capabilities, "rate_limits": client.rate_limits,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "note": "Checks use sample records and API quota. Abstract checks FULL view only; META may still be available. A missing sample does not establish lack of entitlement."}
