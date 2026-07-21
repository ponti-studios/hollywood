import { readFileSync } from 'node:fs';

import { chromium } from 'playwright';
import type { Locator, Page } from 'playwright';

import type { RawRecordRow } from '../../domain/repositories/RawRecordRepository.js';
import { env } from '../../env.js';
import { canonicalizeUrl, emptyBundle, makeStableId } from '../models.js';
import type {
  CreditRow,
  EntityAliasRow,
  EntityRow,
  IngestOptions,
  NormalizedBundle,
  RawPayload,
  SourceDefinition,
} from '../models.js';
import type { Adapter } from './base.js';
import { parseWgaProfileCredits } from './wga-credit-parser.js';

const SEARCH_INPUT_SELECTORS = [
  '#Filter_Keyword',
  "input[name='Filter.Keyword']",
  "input[placeholder='Search writer or project here...']",
];
const SEARCH_TYPE_BUTTON_SELECTORS = ['#search-type', 'button#search-type'];
const SEARCH_BUTTON_SELECTORS = ['#searchBtn', 'button#searchBtn'];
const STARTS_WITH_ITEM_SELECTOR = "a.dropdown-item[data-value='2']";

class SelectorError extends Error {}

function writerKey(url: string): string {
  return makeStableId('wga', canonicalizeUrl(url));
}

export function normalizePrefixes(raw: string): string[] {
  const value = raw.trim();
  if (!value) throw new Error('prefixes must not be empty');
  const prefixes = value.includes(',') ? value.split(',').map((p) => p.trim()) : value.split('');
  const cleaned = prefixes.filter(Boolean);
  if (!cleaned.length) throw new Error('prefixes must contain at least one non-empty prefix');
  return cleaned;
}

function uniqueProfileUrls(urls: string[]): string[] {
  return [...new Set(urls.map(canonicalizeUrl))].sort();
}

async function clickFirstVisible(
  page: Page,
  selectors: string[],
  description: string,
): Promise<void> {
  for (const selector of selectors) {
    const locator = page.locator(selector);
    const count = await locator.count();
    for (let i = 0; i < count; i++) {
      const candidate = locator.nth(i);
      if (await candidate.isVisible()) {
        await candidate.click();
        return;
      }
    }
  }
  throw new SelectorError(
    `Could not find ${description} on ${page.url()} using selectors: ${selectors.join(', ')}`,
  );
}

async function fillFirstVisible(
  page: Page,
  selectors: string[],
  value: string,
  description: string,
): Promise<void> {
  for (const selector of selectors) {
    const locator = page.locator(selector);
    const count = await locator.count();
    for (let i = 0; i < count; i++) {
      const candidate = locator.nth(i);
      if (await candidate.isVisible()) {
        await candidate.fill(value);
        return;
      }
    }
  }
  throw new SelectorError(
    `Could not find ${description} on ${page.url()} using selectors: ${selectors.join(', ')}`,
  );
}

async function searchPrefix(page: Page, prefix: string): Promise<void> {
  await clickFirstVisible(page, SEARCH_TYPE_BUTTON_SELECTORS, 'the search type dropdown');
  await clickFirstVisible(page, [STARTS_WITH_ITEM_SELECTOR], "the 'Starts With' option");
  await fillFirstVisible(page, SEARCH_INPUT_SELECTORS, prefix, 'the search input');
  await clickFirstVisible(page, SEARCH_BUTTON_SELECTORS, "the 'Search' control");
}

async function collectProfileUrls(page: Page): Promise<string[]> {
  const urls = await page
    .locator("a[href*='/member/']")
    .evaluateAll((els) => els.map((a) => (a as HTMLAnchorElement).href));
  return uniqueProfileUrls(urls);
}

async function extractWriterName(profile: Page): Promise<string> {
  // The live WGA directory renders the writer's name in an <h3> under
  // #main-member's header (verified against a real profile page); the <h1>
  // selectors below are the site's older/generic page-banner heading
  // ("Find A Writer") and are kept only as a fallback in case the markup
  // reverts, so they must be tried after the more specific selector.
  for (const selector of ['#main-member h3', '.header h3', 'h1', 'main h1', '.page-title h1']) {
    const locator = profile.locator(selector);
    if (await locator.count()) {
      const text = (await locator.first().innerText()).trim();
      if (text) return text;
    }
  }
  const title = (await profile.title()).trim();
  if (!title) return 'Unknown Writer';
  return title.split(/\s*[|-]\s*/)[0]!.trim() || 'Unknown Writer';
}

/** Maps parsed WGA credits (pure text parsing lives in wga-credit-parser.ts) into bundle rows. */
export function buildWgaCreditRows(
  text: string,
  personEntityId: string,
): { credit: CreditRow; title: EntityRow }[] {
  return parseWgaProfileCredits(text).map((parsed) => {
    const titleEntityId = makeStableId('wga_title', parsed.title);
    return {
      title: {
        entityId: titleEntityId,
        sourceId: 'wga',
        entityType: 'title',
        name: parsed.title,
        canonicalName: parsed.title.toLowerCase(),
        metadataJson: JSON.stringify({ stub: true, category: parsed.category }),
        titleType: parsed.category ?? undefined,
      },
      credit: {
        creditId: makeStableId('wga', personEntityId, parsed.title, parsed.role),
        sourceId: 'wga',
        personEntityId,
        titleEntityId,
        role: parsed.role,
        creditCategory: 'crew',
        billing: parsed.count,
        metadataJson: JSON.stringify({ source: 'wga_profile_text' }),
      },
    };
  });
}

export class WgaAdapter implements Adapter {
  constructor(public source: SourceDefinition) {}

  async fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]> {
    const payloads: RawPayload[] = [];
    const seen = new Set<string>();
    const prefixes =
      options.prefixes ??
      normalizePrefixes(
        String(this.source.metadata['default_prefixes'] ?? 'abcdefghijklmnopqrstuvwxyz'),
      );
    let emitted = 0;

    const browser = await chromium.launch({ headless: true });
    try {
      const context = await browser.newContext({ userAgent: env.HOLLYWOOD_USER_AGENT });
      try {
        const page = await context.newPage();
        for (const prefix of prefixes) {
          if (options.limit !== undefined && emitted >= options.limit) break;
          await page.goto(this.source.defaultUrls[0]!, { waitUntil: 'networkidle' });
          await searchPrefix(page, prefix);
          await page.waitForLoadState('networkidle');

          for (const url of await collectProfileUrls(page)) {
            if (seen.has(url)) continue;
            seen.add(url);

            const profile = await context.newPage();
            let html: string;
            let text: string;
            let name: string;
            try {
              await profile.goto(url, { waitUntil: 'networkidle' });
              html = await profile.content();
              text = await profile.locator('body').innerText();
              name = await extractWriterName(profile);
            } finally {
              await profile.close();
            }

            const canonicalUrl = canonicalizeUrl(url);
            const writerId = writerKey(canonicalUrl);
            const metadata = {
              profileUrl: canonicalUrl,
              writerId,
              writerName: name,
              prefix,
            };

            payloads.push({
              payloadType: 'browser_html',
              logicalId: writerId,
              body: Buffer.from(html, 'utf-8'),
              contentType: 'text/html',
              sourceUrl: canonicalUrl,
              canonicalUrl,
              fetchedAt: new Date(),
              metadata,
              extension: '.html',
            });
            payloads.push({
              payloadType: 'browser_text',
              logicalId: writerId,
              body: Buffer.from(text, 'utf-8'),
              contentType: 'text/plain',
              sourceUrl: canonicalUrl,
              canonicalUrl,
              fetchedAt: new Date(),
              metadata,
              extension: '.txt',
            });

            emitted++;
            if (options.limit !== undefined && emitted >= options.limit) break;
            await new Promise((resolve) => setTimeout(resolve, 2000));
          }
        }
      } finally {
        await context.close();
      }
    } finally {
      await browser.close();
    }

    return payloads;
  }

  async normalizeRawRecords(_runId: string, rawRecords: RawRecordRow[]): Promise<NormalizedBundle> {
    const bundle = emptyBundle();
    for (const record of rawRecords) {
      if (record.payloadType !== 'browser_text') continue;
      const path = record.contentPath;
      const metadata = JSON.parse(record.metadataJson ?? '{}');
      const text = readFileSync(path, 'utf-8');
      const writerName = metadata.writerName ?? 'Unknown Writer';
      const writerId =
        metadata.writerId ?? writerKey(record.canonicalUrl ?? record.sourceUrl ?? '');
      const entityId = makeStableId('wga', 'person', String(writerId));

      const entityRow: EntityRow = {
        entityId,
        sourceId: this.source.sourceId,
        externalId: String(writerId),
        entityType: 'person',
        name: String(writerName),
        canonicalName: String(writerName).toLowerCase(),
        metadataJson: JSON.stringify({
          profileUrl: metadata.profileUrl ?? null,
          rawRecordId: record.id,
        }),
      };
      bundle.entities.push(entityRow);

      const aliasRow: EntityAliasRow = {
        entityAliasId: makeStableId(entityId, String(writerName)),
        entityId,
        sourceId: this.source.sourceId,
        alias: String(writerName),
      };
      bundle.entityAliases.push(aliasRow);

      for (const { credit, title } of buildWgaCreditRows(text, entityId)) {
        bundle.entities.push(title);
        bundle.credits.push(credit);
      }
    }
    return bundle;
  }
}
