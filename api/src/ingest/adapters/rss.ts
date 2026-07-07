import { readFileSync } from "node:fs";
import Parser from "rss-parser";
import { env } from "../../env.js";
import { stripHtmlFragment, extractTextFromHtml } from "../extractors.js";
import {
  canonicalizeUrl,
  emptyBundle,
  extendBundle,
  makeStableId,
  normalizeWhitespace,
} from "../models.js";
import type {
  ArticleContentRow,
  ArticleEntityRow,
  ArticleRow,
  EntityAliasRow,
  EntityRow,
  IngestOptions,
  NormalizedBundle,
  RawPayload,
  SourceDefinition,
} from "../models.js";
import type { Adapter } from "./base.js";
import type { DbRow } from "../../db/index.js";

interface FeedItem {
  title?: string;
  link?: string;
  pubDate?: string;
  isoDate?: string;
  creator?: string;
  content?: string;
  contentSnippet?: string;
  summary?: string;
  guid?: string;
  categories?: string[];
}

function entryPublished(item: FeedItem): string {
  return item.isoDate ?? item.pubDate ?? "";
}

export class RssAdapter implements Adapter {
  private parser = new Parser<object, FeedItem>({
    customFields: { item: [["dc:creator", "creator"]] },
  });

  constructor(public source: SourceDefinition) {}

  async fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]> {
    const headers = { "User-Agent": env.HOLLYWOOD_USER_AGENT };
    const payloads: RawPayload[] = [];
    let remaining = options.limit;

    for (const feedUrl of this.source.defaultUrls) {
      const response = await fetch(feedUrl, { headers, signal: AbortSignal.timeout(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000) });
      if (!response.ok) throw new Error(`Failed to fetch feed ${feedUrl}: ${response.status}`);
      const bodyText = await response.text();
      const feed = await this.parser.parseString(bodyText);
      let entries = feed.items ?? [];

      if (options.since) {
        entries = entries.filter((entry) => {
          const published = entryPublished(entry);
          if (!published) return true;
          const publishedAt = new Date(published);
          return isNaN(publishedAt.getTime()) || publishedAt >= options.since!;
        });
      }

      let selectedEntries = entries;
      if (remaining !== undefined) {
        selectedEntries = entries.slice(0, remaining);
        remaining -= selectedEntries.length;
      }

      const selectedUrls = selectedEntries.filter((e) => e.link).map((e) => canonicalizeUrl(e.link!));

      payloads.push({
        payloadType: "feed_xml",
        logicalId: feedUrl,
        body: Buffer.from(bodyText, "utf-8"),
        contentType: response.headers.get("content-type") ?? "application/rss+xml",
        sourceUrl: feedUrl,
        fetchedAt: new Date(),
        metadata: { feed_url: feedUrl, selected_urls: selectedUrls },
        extension: ".xml",
      });

      if (options.fullText) {
        for (const entry of selectedEntries) {
          if (!entry.link) continue;
          const articleResponse = await fetch(entry.link, { headers, signal: AbortSignal.timeout(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000) });
          if (!articleResponse.ok) continue;
          const articleBody = Buffer.from(await articleResponse.arrayBuffer());
          const canonicalUrl = canonicalizeUrl(articleResponse.url || entry.link);
          payloads.push({
            payloadType: "article_html",
            logicalId: canonicalUrl,
            body: articleBody,
            contentType: articleResponse.headers.get("content-type") ?? "text/html",
            sourceUrl: entry.link,
            canonicalUrl,
            fetchedAt: new Date(),
            metadata: { feed_url: feedUrl, title: entry.title ?? "" },
            extension: ".html",
          });
        }
      }

      if (remaining !== undefined && remaining <= 0) break;
    }

    return payloads;
  }

  async normalizeRawRecords(runId: string, rawRecords: DbRow[]): Promise<NormalizedBundle> {
    const bundle = emptyBundle();
    for (const record of rawRecords) {
      const payloadType = String(record["payload_type"]);
      const path = String(record["content_path"]);
      const metadata = JSON.parse(String(record["metadata_json"] ?? "{}"));

      if (payloadType === "feed_xml") {
        extendBundle(bundle, await this.normalizeFeedXml(runId, record, path, metadata));
      } else if (payloadType === "article_html") {
        extendBundle(bundle, this.normalizeArticleHtml(record, path));
      }
    }
    return bundle;
  }

  private async normalizeFeedXml(runId: string, record: DbRow, path: string, metadata: { feed_url?: string; selected_urls?: string[] }): Promise<NormalizedBundle> {
    const bundle = emptyBundle();
    const xml = readFileSync(path, "utf-8");
    const feed = await this.parser.parseString(xml);
    const selectedUrls = new Set(metadata.selected_urls ?? []);

    for (const entry of feed.items ?? []) {
      if (!entry.link) continue;
      const canonicalUrl = canonicalizeUrl(entry.link);
      if (selectedUrls.size && !selectedUrls.has(canonicalUrl)) continue;

      const articleId = makeStableId(this.source.sourceId, canonicalUrl);
      const publishedRaw = entryPublished(entry);
      const publishedAt = publishedRaw ? new Date(publishedRaw) : undefined;
      const author = entry.creator || undefined;
      const categories = entry.categories ?? [];

      const article: ArticleRow = {
        articleId,
        sourceId: this.source.sourceId,
        canonicalUrl,
        url: entry.link,
        title: normalizeWhitespace(entry.title ?? ""),
        author,
        publishedAt: publishedAt && !isNaN(publishedAt.getTime()) ? publishedAt : undefined,
        summary: stripHtmlFragment(entry.summary ?? entry.contentSnippet),
        feedGuid: entry.guid || canonicalUrl,
        licenseClass: this.source.licenseClass,
        runId,
        metadataJson: JSON.stringify({ feed_url: metadata.feed_url, categories }),
      };
      bundle.articles.push(article);

      const descriptionText = stripHtmlFragment(entry.summary ?? entry.contentSnippet);
      if (descriptionText) {
        const row: ArticleContentRow = {
          contentId: makeStableId(articleId, "feed_description"),
          articleId,
          sourceId: this.source.sourceId,
          contentKind: "feed_description",
          text: descriptionText,
          rawRecordId: String(record["id"]),
          contentHash: String(record["content_hash"]),
          licenseClass: this.source.licenseClass,
          metadataJson: "{}",
        };
        bundle.articleContent.push(row);
      }

      if (entry.content) {
        const encodedText = stripHtmlFragment(entry.content);
        if (encodedText) {
          const row: ArticleContentRow = {
            contentId: makeStableId(articleId, "feed_content"),
            articleId,
            sourceId: this.source.sourceId,
            contentKind: "feed_content",
            text: encodedText,
            rawRecordId: String(record["id"]),
            contentHash: String(record["content_hash"]),
            licenseClass: this.source.licenseClass,
            metadataJson: "{}",
          };
          bundle.articleContent.push(row);
        }
      }

      if (author) {
        const entityId = makeStableId(this.source.sourceId, "person", author.toLowerCase());
        const entityRow: EntityRow = {
          entityId,
          sourceId: this.source.sourceId,
          entityType: "person",
          name: author,
          canonicalName: author.toLowerCase(),
          licenseClass: this.source.licenseClass,
          metadataJson: JSON.stringify({ role: "author" }),
        };
        bundle.entities.push(entityRow);
        const aliasRow: EntityAliasRow = {
          entityAliasId: makeStableId(entityId, author),
          entityId,
          sourceId: this.source.sourceId,
          alias: author,
        };
        bundle.entityAliases.push(aliasRow);
        const articleEntityRow: ArticleEntityRow = {
          articleEntityId: makeStableId(articleId, entityId, "author"),
          articleId,
          entityId,
          sourceId: this.source.sourceId,
          relation: "author",
          metadataJson: "{}",
        };
        bundle.articleEntities.push(articleEntityRow);
      }
    }
    return bundle;
  }

  private normalizeArticleHtml(record: DbRow, path: string): NormalizedBundle {
    const bundle = emptyBundle();
    const articleUrl = String(record["canonical_url"] ?? record["source_url"]);
    const articleId = makeStableId(this.source.sourceId, canonicalizeUrl(articleUrl));
    const html = readFileSync(path, "utf-8");
    const extracted = extractTextFromHtml(html);
    if (extracted) {
      const row: ArticleContentRow = {
        contentId: makeStableId(articleId, "page_extract"),
        articleId,
        sourceId: this.source.sourceId,
        contentKind: "page_extract",
        text: extracted,
        rawRecordId: String(record["id"]),
        contentHash: String(record["content_hash"]),
        licenseClass: this.source.licenseClass,
        metadataJson: JSON.stringify({ source_url: record["source_url"] }),
      };
      bundle.articleContent.push(row);
    }
    return bundle;
  }
}
