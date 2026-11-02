from .provenance import with_provenance
from .validation import identifier

from ..client import ScopusClient
from ..formatters import format_author_profile

AUTHOR_INST_NOTE = (
    "Elsevier denied author profile access. Check the API key and endpoint entitlement "
    "with scopus check; an institutional token (SCOPUS_INST_TOKEN) or approved network may be required."
)


async def do_get_author(client: ScopusClient, author_id: str) -> dict:
    clean = identifier(author_id, "author_id")
    raw = await client.request(
        f"/content/author/author_id/{clean}",
        params={"view": "ENHANCED"},
    )
    return with_provenance(format_author_profile(raw), client)

