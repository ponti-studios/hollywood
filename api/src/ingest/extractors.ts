import { JSDOM } from "jsdom";
import { Readability } from "@mozilla/readability";
import { normalizeWhitespace } from "./models.js";

const HTML_TAG_RE = /<[^>]+>/g;

function unescapeHtml(value: string): string {
  return value
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(parseInt(dec, 10)))
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&nbsp;/g, " ");
}

export function stripHtmlFragment(value: string | null | undefined): string {
  if (!value) return "";
  const unescaped = unescapeHtml(value);
  const stripped = unescaped.replace(HTML_TAG_RE, " ");
  return normalizeWhitespace(stripped);
}

export function extractTextFromHtml(document: string): string {
  try {
    const dom = new JSDOM(document, { url: "https://example.com" });
    const reader = new Readability(dom.window.document);
    const article = reader.parse();
    if (article?.textContent) {
      return normalizeWhitespace(article.textContent);
    }
  } catch {
    // fall through to the regex-based fallback below
  }
  return stripHtmlFragment(document);
}
