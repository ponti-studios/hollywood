import type { SourceDefinition } from "./models.js";

export const BUILTIN_SOURCES: readonly SourceDefinition[] = [
  {
    sourceId: "variety",
    name: "Variety RSS",
    kind: "rss",
    description: "Entertainment trade news feed from Variety.",
    groups: ["news", "all"],
    defaultUrls: ["https://variety.com/feed/"],
    licenseClass: "web_copyright",
    archiveModes: ["feed_xml", "article_html", "extracted_text"],
    fetchStrategy: "rss_feed",
    defaultFullText: true,
    metadata: {},
  },
  {
    sourceId: "deadline",
    name: "Deadline RSS",
    kind: "rss",
    description: "Entertainment trade news feed from Deadline.",
    groups: ["news", "all"],
    defaultUrls: ["https://deadline.com/feed/"],
    licenseClass: "web_copyright",
    archiveModes: ["feed_xml", "article_html", "extracted_text"],
    fetchStrategy: "rss_feed",
    defaultFullText: true,
    metadata: {},
  },
  {
    sourceId: "hollywood_reporter",
    name: "The Hollywood Reporter RSS",
    kind: "rss",
    description: "Entertainment trade news feed from The Hollywood Reporter.",
    groups: ["news", "all"],
    defaultUrls: ["https://www.hollywoodreporter.com/feed/"],
    licenseClass: "web_copyright",
    archiveModes: ["feed_xml", "article_html", "extracted_text"],
    fetchStrategy: "rss_feed",
    defaultFullText: true,
    metadata: {},
  },
  {
    sourceId: "the_wrap",
    name: "TheWrap RSS",
    kind: "rss",
    description: "Entertainment trade news feed from TheWrap.",
    groups: ["news", "all"],
    defaultUrls: ["https://www.thewrap.com/feed/"],
    licenseClass: "web_copyright",
    archiveModes: ["feed_xml", "article_html", "extracted_text"],
    fetchStrategy: "rss_feed",
    defaultFullText: true,
    metadata: {},
  },
  {
    sourceId: "wga",
    name: "WGA Directory",
    kind: "browser",
    description: "WGA directory crawl for writer profiles and credit summaries.",
    groups: ["directories", "entities", "all"],
    defaultUrls: ["https://directories.wga.org/"],
    licenseClass: "research_non_commercial",
    archiveModes: ["browser_html", "browser_text"],
    fetchStrategy: "playwright_directory",
    defaultFullText: true,
    metadata: { default_prefixes: "abcdefghijklmnopqrstuvwxyz" },
  },
  {
    sourceId: "imdb",
    name: "IMDb Datasets",
    kind: "dataset",
    description: "IMDb non-commercial datasets sliced into raw archives and normalized entities.",
    groups: ["entities", "all"],
    defaultUrls: [
      "https://datasets.imdbws.com/name.basics.tsv.gz",
      "https://datasets.imdbws.com/title.basics.tsv.gz",
      "https://datasets.imdbws.com/title.principals.tsv.gz",
    ],
    licenseClass: "research_non_commercial",
    archiveModes: ["dataset_tsv"],
    fetchStrategy: "streamed_dataset",
    defaultFullText: true,
    metadata: {},
  },
  {
    sourceId: "tmdb",
    name: "TMDb API",
    kind: "api",
    description: "TMDb API enrichment for people, titles, external IDs, and credits.",
    groups: ["entities", "all"],
    defaultUrls: ["https://api.themoviedb.org/3/trending/all/day"],
    licenseClass: "api_terms",
    archiveModes: ["api_json"],
    fetchStrategy: "api_trending",
    apiKeyEnv: "TMDB_API_KEY",
    defaultFullText: false,
    metadata: {},
  },
  {
    sourceId: "wikidata",
    name: "Wikidata Entertainment Query",
    kind: "dataset",
    description: "Selective Wikidata enrichment for film-industry entities.",
    groups: ["entities", "all"],
    defaultUrls: ["https://query.wikidata.org/sparql"],
    licenseClass: "public_knowledge",
    archiveModes: ["api_json"],
    fetchStrategy: "sparql_query",
    defaultFullText: false,
    metadata: {},
  },
];

const SOURCES_BY_ID = new Map(BUILTIN_SOURCES.map((s) => [s.sourceId, s]));

export function getSource(sourceId: string): SourceDefinition {
  const source = SOURCES_BY_ID.get(sourceId);
  if (!source) throw new Error(`Unknown source: ${sourceId}`);
  return source;
}

export function listSources(group?: string): SourceDefinition[] {
  if (!group) return [...BUILTIN_SOURCES];
  return BUILTIN_SOURCES.filter((s) => s.groups.includes(group));
}
