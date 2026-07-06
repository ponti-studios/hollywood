from __future__ import annotations

from .models import LicenseClass, SourceDefinition, SourceKind

BUILTIN_SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        source_id="variety",
        name="Variety RSS",
        kind=SourceKind.RSS,
        description="Entertainment trade news feed from Variety.",
        groups=("news", "all"),
        default_urls=("https://variety.com/feed/",),
        license_class=LicenseClass.WEB_COPYRIGHT,
        archive_modes=("feed_xml", "article_html", "extracted_text"),
        fetch_strategy="rss_feed",
    ),
    SourceDefinition(
        source_id="deadline",
        name="Deadline RSS",
        kind=SourceKind.RSS,
        description="Entertainment trade news feed from Deadline.",
        groups=("news", "all"),
        default_urls=("https://deadline.com/feed/",),
        license_class=LicenseClass.WEB_COPYRIGHT,
        archive_modes=("feed_xml", "article_html", "extracted_text"),
        fetch_strategy="rss_feed",
    ),
    SourceDefinition(
        source_id="hollywood_reporter",
        name="The Hollywood Reporter RSS",
        kind=SourceKind.RSS,
        description="Entertainment trade news feed from The Hollywood Reporter.",
        groups=("news", "all"),
        default_urls=("https://www.hollywoodreporter.com/feed/",),
        license_class=LicenseClass.WEB_COPYRIGHT,
        archive_modes=("feed_xml", "article_html", "extracted_text"),
        fetch_strategy="rss_feed",
    ),
    SourceDefinition(
        source_id="the_wrap",
        name="TheWrap RSS",
        kind=SourceKind.RSS,
        description="Entertainment trade news feed from TheWrap.",
        groups=("news", "all"),
        default_urls=("https://www.thewrap.com/feed/",),
        license_class=LicenseClass.WEB_COPYRIGHT,
        archive_modes=("feed_xml", "article_html", "extracted_text"),
        fetch_strategy="rss_feed",
    ),
    SourceDefinition(
        source_id="wga",
        name="WGA Directory",
        kind=SourceKind.BROWSER,
        description="WGA directory crawl for writer profiles and credit summaries.",
        groups=("directories", "entities", "all"),
        default_urls=("https://directories.wga.org/",),
        license_class=LicenseClass.RESEARCH_NON_COMMERCIAL,
        archive_modes=("browser_html", "browser_text"),
        fetch_strategy="playwright_directory",
        metadata={"default_prefixes": "abcdefghijklmnopqrstuvwxyz"},
    ),
    SourceDefinition(
        source_id="imdb",
        name="IMDb Datasets",
        kind=SourceKind.DATASET,
        description="IMDb non-commercial datasets sliced into raw archives and normalized entities.",
        groups=("entities", "all"),
        default_urls=(
            "https://datasets.imdbws.com/name.basics.tsv.gz",
            "https://datasets.imdbws.com/title.basics.tsv.gz",
            "https://datasets.imdbws.com/title.principals.tsv.gz",
        ),
        license_class=LicenseClass.RESEARCH_NON_COMMERCIAL,
        archive_modes=("dataset_tsv",),
        fetch_strategy="streamed_dataset",
    ),
    SourceDefinition(
        source_id="tmdb",
        name="TMDb API",
        kind=SourceKind.API,
        description="TMDb API enrichment for people, titles, external IDs, and credits.",
        groups=("entities", "all"),
        default_urls=("https://api.themoviedb.org/3/trending/all/day",),
        license_class=LicenseClass.API_TERMS,
        archive_modes=("api_json",),
        fetch_strategy="api_trending",
        api_key_env="TMDB_API_KEY",
        default_full_text=False,
    ),
    SourceDefinition(
        source_id="wikidata",
        name="Wikidata Entertainment Query",
        kind=SourceKind.DATASET,
        description="Selective Wikidata enrichment for film-industry entities.",
        groups=("entities", "all"),
        default_urls=("https://query.wikidata.org/sparql",),
        license_class=LicenseClass.PUBLIC_KNOWLEDGE,
        archive_modes=("api_json",),
        fetch_strategy="sparql_query",
        default_full_text=False,
    ),
)


SOURCES_BY_ID = {source.source_id: source for source in BUILTIN_SOURCES}


def get_source(source_id: str) -> SourceDefinition:
    try:
        return SOURCES_BY_ID[source_id]
    except KeyError as exc:
        raise KeyError(f"Unknown source: {source_id}") from exc


def list_sources(group: str | None = None) -> list[SourceDefinition]:
    sources = list(BUILTIN_SOURCES)
    if group is None:
        return sources
    return [source for source in sources if group in source.groups]
