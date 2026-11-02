"""Public result contracts. Unknown metrics are null, never inferred zeros."""
from pydantic import BaseModel, ConfigDict, Field


class ResultModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    retrieved_at: str | None = None
    served_at: str | None = None
    source: str = "scopus"


class Paper(ResultModel):
    scopus_id: str = ""
    title: str = ""
    doi: str | None = None
    cited_by_count: int | None = None
    open_access: bool | None = None
    publication: str = ""
    cover_date: str = ""


class PaperAuthor(ResultModel):
    name: str
    scopus_author_id: str | None = None
    affiliation: str | None = None


class AbstractResult(Paper):
    abstract: str | None = None
    authors: list[PaperAuthor] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    subject_areas: list[str] = Field(default_factory=list)
    access_note: str | None = None


class Author(ResultModel):
    author_id: str
    name: str
    document_count: int | None = None
    orcid: str | None = None


class AuthorProfile(Author):
    h_index: int | None = None
    citation_count: int | None = None
    cited_by_count: int | None = None
    subject_areas: list[str] = Field(default_factory=list)


class Affiliation(ResultModel):
    affiliation_id: str = ""
    name: str = ""
    document_count: int | None = None
    city: str | None = None
    country: str | None = None


class SearchPage(ResultModel):
    total_results: int
    showing: int
    start_index: int = 0
    items_per_page: int = 0
    query: str = ""
    next_start: int | None = None
    truncated: bool = False
    complete_corpus: bool = False
    stop_reason: str = "complete"


class PaperSearchResult(SearchPage):
    papers: list[Paper]


class AuthorSearchResult(SearchPage):
    authors: list[Author]


class AffiliationSearchResult(SearchPage):
    affiliations: list[Affiliation]


class CitationCountResult(ResultModel):
    scopus_id: str = ""
    doi: str | None = None
    cited_by_count: int | None
    self_citation_count: int | None = None


class CitationsOverviewResult(ResultModel):
    total_citations: int | None
    citations_by_year: dict[str, int | None]


class BatchItem(ResultModel):
    identifier: str
    ok: bool
    data: AbstractResult | None = None
    error: str | None = None


class BatchAbstractResult(ResultModel):
    results: list[BatchItem]
    succeeded: int
    failed: int
