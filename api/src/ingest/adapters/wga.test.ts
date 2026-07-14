import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { buildWgaCreditRows } from './wga.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

function fixture(name: string): string {
  return readFileSync(resolve(__dirname, '__fixtures__/wga', name), 'utf-8');
}

// Same real-fixture convention as wga-credit-parser.test.ts — proves the
// adapter actually wires the parsed category into EntityRow.titleType,
// not just that the parser itself extracts it correctly.
describe('buildWgaCreditRows', () => {
  it('sets title.titleType from the table-format category', () => {
    const text = fixture('benedict_fitzgerald_deceased.txt');
    const rows = buildWgaCreditRows(text, 'person-id');
    const inColdBlood = rows.find((r) => r.title.name === 'In Cold Blood');
    expect(inColdBlood?.title.titleType).toBe('Television');
  });

  it('sets title.titleType from the summary-format category', () => {
    const text = fixture('ben_montanio.txt');
    const rows = buildWgaCreditRows(text, 'person-id');
    const babyDaddy = rows.find((r) => r.title.name === 'Baby Daddy');
    expect(babyDaddy?.title.titleType).toBe('Series');
  });
});
