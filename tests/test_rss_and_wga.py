from __future__ import annotations

from pathlib import Path

from hollywood.adapters.rss import RssAdapter
from hollywood.adapters.wga import normalize_prefixes, unique_profile_urls, writer_key
from hollywood.config import HollywoodSettings
from hollywood.registry import get_source
from hollywood.storage import HollywoodStorage

FIXTURES = Path(__file__).parent / "fixtures"


def test_wga_helpers_are_stable() -> None:
    assert normalize_prefixes("abc") == ["a", "b", "c"]
    assert normalize_prefixes("a,b, c") == ["a", "b", "c"]
    assert unique_profile_urls(
        [
            "https://directories.wga.org/member/b/",
            "https://directories.wga.org/member/a/?utm_source=test",
            "https://directories.wga.org/member/b/",
        ]
    ) == [
        "https://directories.wga.org/member/a",
        "https://directories.wga.org/member/b",
    ]
    assert writer_key("https://directories.wga.org/member/example/") == writer_key(
        "https://directories.wga.org/member/example"
    )


def test_rss_normalization_builds_articles_and_bodies(tmp_path: Path) -> None:
    settings = HollywoodSettings(
        data_dir=tmp_path / "data", db_path=tmp_path / "data" / "hollywood.duckdb"
    )
    storage = HollywoodStorage(settings.db_path)
    storage.initialize()
    source = get_source("variety")
    adapter = RssAdapter(source)

    feed_path = tmp_path / "feed.xml"
    feed_path.write_bytes((FIXTURES / "rss" / "variety.xml").read_bytes())
    article_path = tmp_path / "article.html"
    article_path.write_text(
        (FIXTURES / "article.html").read_text(encoding="utf-8"), encoding="utf-8"
    )

    raw_records = [
        {
            "raw_record_id": "feed-1",
            "payload_type": "feed_xml",
            "content_path": str(feed_path),
            "content_hash": "hash-feed",
            "source_url": "https://variety.com/feed/",
            "canonical_url": None,
            "metadata_json": '{"feed_url":"https://variety.com/feed/","selected_urls":["https://variety.com/2026/film/news/example-hollywood-story"]}',
        },
        {
            "raw_record_id": "article-1",
            "payload_type": "article_html",
            "content_path": str(article_path),
            "content_hash": "hash-article",
            "source_url": "https://variety.com/2026/film/news/example-hollywood-story/?utm_source=test",
            "canonical_url": "https://variety.com/2026/film/news/example-hollywood-story",
            "metadata_json": '{"title":"Example Hollywood Story"}',
        },
    ]

    bundle = adapter.normalize_raw_records(settings, storage, "run-1", raw_records)
    assert len(bundle.articles) == 1
    assert len(bundle.article_bodies) >= 2
    assert (
        bundle.articles[0].canonical_url
        == "https://variety.com/2026/film/news/example-hollywood-story"
    )
    assert any(body.body_kind == "page_extract" for body in bundle.article_bodies)
    assert any(entity.name == "Jane Reporter" for entity in bundle.entities)
