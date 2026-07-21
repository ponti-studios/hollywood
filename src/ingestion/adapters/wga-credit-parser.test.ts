import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  parseSummaryFormatCredits,
  parseTableFormatCredits,
  parseWgaProfileCredits,
} from './wga-credit-parser.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

function fixture(name: string): string {
  return readFileSync(resolve(__dirname, '__fixtures__/wga', name), 'utf-8');
}

// These fixtures are real `body.innerText()` captures saved from raw_records
// during a live WGA ingest run — not hand-written strings. If the site
// markup changes, re-scrape and replace the fixture rather than editing it
// by hand, so the test keeps proving the parser against real output.

describe('parseSummaryFormatCredits', () => {
  it("parses the 'N Credits' summary section", () => {
    const text = fixture('ben_montanio.txt');
    const results = parseSummaryFormatCredits(text);
    expect(results).toHaveLength(16);
    expect(results).toContainEqual({
      title: 'Baby Daddy',
      category: 'Series',
      role: 'writer',
      count: 13,
    });
    expect(results).toContainEqual({
      title: 'Wizards Of Waverly Place',
      category: 'Series',
      role: 'writer',
      count: 18,
    });
    expect(results).toContainEqual({
      title: 'Night Court',
      category: 'Series',
      role: 'writer',
      count: 2,
    });
  });

  it('does not fire on a profile with no summary section', () => {
    const text = fixture('benedict_fitzgerald_deceased.txt');
    expect(parseSummaryFormatCredits(text)).toEqual([]);
  });
});

describe('parseTableFormatCredits', () => {
  it('parses a table-layout profile with multiple single-role entries', () => {
    const text = fixture('benedict_fitzgerald_deceased.txt');
    const results = parseTableFormatCredits(text);
    expect(results).toEqual([
      { title: 'In Cold Blood', category: 'Television', role: 'teleplay' },
      { title: 'Heart of Darkness', category: 'Television', role: 'teleplay' },
      { title: 'Zelda', category: 'Television', role: 'written' },
    ]);
  });

  it('captures multiple distinct roles on the same title (e.g. teleplay + story)', () => {
    const text = fixture('ben_montanio.txt');
    const results = parseTableFormatCredits(text);
    const afterShock = results.filter((r) => r.title === 'After Shock');
    expect(afterShock).toContainEqual({
      title: 'After Shock',
      category: 'Pilot/Pending Series',
      role: 'teleplay',
    });
    expect(afterShock).toContainEqual({
      title: 'After Shock',
      category: 'Pilot/Pending Series',
      role: 'story',
    });

    const zappedAgain = results.filter((r) => r.title === 'Zapped Again');
    expect(zappedAgain).toContainEqual({
      title: 'Zapped Again',
      category: 'Television',
      role: 'teleplay',
    });
    expect(zappedAgain).toContainEqual({
      title: 'Zapped Again',
      category: 'Television',
      role: 'story',
    });
  });

  it('does not fire on a profile with no table section', () => {
    // ben_montanio.txt also has a summary section earlier in the page —
    // confirms the table parser only reacts to its own trigger pattern
    // and ignores the summary-format lines entirely.
    const text = fixture('ben_montanio.txt');
    const results = parseTableFormatCredits(text);
    expect(
      results.every((r) =>
        [
          'The Wizards Return: Alex vs. Alex',
          'Wendy Wu: Homecoming Warrior',
          'After Shock',
          'Zapped Again',
        ].includes(r.title),
      ),
    ).toBe(true);
  });
});

describe('parseWgaProfileCredits', () => {
  it('merges both formats when a single profile page mixes them', () => {
    const text = fixture('ben_montanio.txt');
    const results = parseWgaProfileCredits(text);
    // 16 from the summary section + 6 from the table section
    // (4 titles, 2 of which carry two distinct roles)
    expect(results).toHaveLength(22);
  });

  it('returns only table-format results for a table-only profile', () => {
    const text = fixture('benedict_fitzgerald_deceased.txt');
    const results = parseWgaProfileCredits(text);
    expect(results).toHaveLength(3);
  });

  it('returns nothing for text with no recognizable credit section', () => {
    expect(parseWgaProfileCredits('Members\nEmployers & Agents\nSEARCH\n')).toEqual([]);
  });
});
