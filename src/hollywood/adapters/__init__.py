from __future__ import annotations

from ..models import SourceDefinition, SourceKind
from .base import BaseAdapter
from .imdb import ImdbAdapter
from .rss import RssAdapter
from .tmdb import TmdbAdapter
from .wga import WgaAdapter
from .wikidata import WikidataAdapter


def get_adapter(source: SourceDefinition) -> BaseAdapter:
    if source.kind == SourceKind.RSS:
        return RssAdapter(source)
    if source.source_id == "wga":
        return WgaAdapter(source)
    if source.source_id == "imdb":
        return ImdbAdapter(source)
    if source.source_id == "tmdb":
        return TmdbAdapter(source)
    if source.source_id == "wikidata":
        return WikidataAdapter(source)
    raise KeyError(f"No adapter for source {source.source_id}")
