/**
 * Pure text parsers for WGA writer-directory profile pages.
 *
 * A single profile page can mix multiple layouts in different sections (e.g.
 * a "Television Series Writing Credits" summary section alongside a
 * "TV Movies, Specials & Pilots" table section on the same page). Every
 * parser below runs independently against the full page text and results
 * are merged — a parser only produces rows when its own trigger pattern
 * matches, so running all of them is safe.
 *
 * To support a new WGA profile layout: write a pure `(text) =>
 * ParsedWgaCredit[]` function below and add it to CREDIT_FORMAT_PARSERS.
 * Nothing else needs to change. No I/O, no Playwright — these take the
 * already-scraped `body.innerText()` string, so they're testable directly
 * against fixture text saved from real `raw_records` rows.
 */

export interface ParsedWgaCredit {
  title: string;
  category: string | null;
  role: string;
  count?: number;
}

type CreditFormatParser = (text: string) => ParsedWgaCredit[];

const CREDIT_COUNT_RE = /^(\d+)\s+Credits?$/;
const TITLE_CATEGORY_RE = /^(.+?)\s*\(([^)]+)\)\s*$/;
const TABLE_ENTRY_START_RE = /^(.+?)\s*\(([^)]+)\)\t(\d{2}\/\d{2}\/\d{4})\t?$/;
const WRITING_CREDIT_LINE_RE = /^(Teleplay|Written|Story|Created|Developed)\s+by:\s*(.+)$/i;
const NON_TITLE_LINE_PREFIXES = [
  'Created by:',
  'Written by:',
  'Teleplay by:',
  'Story by:',
  'Developed by:',
];

/**
 * Format 1 — "count summary" layout, e.g. under "Television Series Writing Credits":
 *   Title (Category)
 *   Created by: ...
 *   Genre
 *   N Credits
 */
export function parseSummaryFormatCredits(text: string): ParsedWgaCredit[] {
  const results: ParsedWgaCredit[] = [];
  let previousTitle: string | null = null;
  let previousCategory: string | null = null;

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    const countMatch = CREDIT_COUNT_RE.exec(line);
    if (countMatch && previousTitle) {
      results.push({
        title: previousTitle,
        category: previousCategory,
        role: 'writer',
        count: parseInt(countMatch[1]!, 10),
      });
      previousTitle = null;
      previousCategory = null;
      continue;
    }

    if (
      !NON_TITLE_LINE_PREFIXES.some((prefix) => line.startsWith(prefix)) &&
      !line.includes('Writers Guild') &&
      !line.includes('Jump To') &&
      line.includes('(')
    ) {
      const titleMatch = TITLE_CATEGORY_RE.exec(line);
      previousTitle = titleMatch ? titleMatch[1]!.trim() : line;
      previousCategory = titleMatch ? titleMatch[2]!.trim() : null;
    }
  }
  return results;
}

/**
 * Format 2 — "table" layout, e.g. under "TV Movies, Specials & Pilots":
 *   Title (Category)<TAB>MM/DD/YYYY<TAB>
 *   Teleplay by: ...
 *   Story by: ...
 *   <TAB>Genre
 *
 * One row per "<Role> by:" line found before the terminating tab-prefixed
 * line — a title can carry more than one distinct writing-credit role
 * (e.g. both a "Story by" and a "Teleplay by" credit on the same project).
 */
export function parseTableFormatCredits(text: string): ParsedWgaCredit[] {
  const results: ParsedWgaCredit[] = [];
  let current: { title: string; category: string; roles: Set<string> } | null = null;

  const flush = () => {
    if (current) {
      for (const role of current.roles) {
        results.push({ title: current.title, category: current.category, role });
      }
    }
    current = null;
  };

  for (const rawLine of text.split('\n')) {
    if (rawLine.startsWith('\t')) {
      flush();
      continue;
    }
    const trimmed = rawLine.trim();
    if (!trimmed) continue;

    const startMatch = TABLE_ENTRY_START_RE.exec(rawLine);
    if (startMatch) {
      flush();
      current = { title: startMatch[1]!.trim(), category: startMatch[2]!.trim(), roles: new Set() };
      continue;
    }

    if (current) {
      const creditMatch = WRITING_CREDIT_LINE_RE.exec(trimmed);
      if (creditMatch) current.roles.add(creditMatch[1]!.toLowerCase());
    }
  }
  flush();
  return results;
}

export const CREDIT_FORMAT_PARSERS: readonly CreditFormatParser[] = [
  parseSummaryFormatCredits,
  parseTableFormatCredits,
];

/** Runs every known format parser against the page text and merges results, deduped by (title, role). */
export function parseWgaProfileCredits(text: string): ParsedWgaCredit[] {
  const results: ParsedWgaCredit[] = [];
  const seen = new Set<string>();
  for (const parser of CREDIT_FORMAT_PARSERS) {
    for (const credit of parser(text)) {
      const key = `${credit.title}::${credit.role}`;
      if (seen.has(key)) continue;
      seen.add(key);
      results.push(credit);
    }
  }
  return results;
}
