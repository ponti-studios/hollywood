import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';

import { getDrizzle } from '../index.js';
import {
  runs,
  rawRecords,
  articles,
  articleContent,
  articleEntities,
  people,
  titles,
  companies,
  aliases,
  credits,
} from '../schema.js';
import * as schema from '../schema.js';

type Db = BetterSQLite3Database<typeof schema>;

const EXPORTABLE_TABLES = [
  'runs',
  'raw_records',
  'articles',
  'article_content',
  'article_entities',
  'people',
  'titles',
  'companies',
  'aliases',
  'credits',
] as const;

const TABLE_QUERIES: Record<string, (db: Db) => unknown[]> = {
  runs: (db) => db.select().from(runs).all(),
  raw_records: (db) => db.select().from(rawRecords).all(),
  articles: (db) => db.select().from(articles).all(),
  article_content: (db) => db.select().from(articleContent).all(),
  article_entities: (db) => db.select().from(articleEntities).all(),
  people: (db) => db.select().from(people).all(),
  titles: (db) => db.select().from(titles).all(),
  companies: (db) => db.select().from(companies).all(),
  aliases: (db) => db.select().from(aliases).all(),
  credits: (db) => db.select().from(credits).all(),
};

export class ExportService {
  constructor(private db: Db = getDrizzle()) {}

  count(table: string): number {
    if (!this.isExportable(table)) throw new Error(`Unknown table: ${table}`);
    const query = TABLE_QUERIES[table];
    return query(this.db).length;
  }

  exportTable(table: string, outputDir: string, format: 'jsonl' | 'parquet'): string {
    if (!this.isExportable(table)) throw new Error(`Unknown table: ${table}`);
    if (format === 'parquet') {
      throw new Error('parquet export is not yet supported; use format=jsonl');
    }

    mkdirSync(outputDir, { recursive: true });
    const path = resolve(outputDir, `${table}.jsonl`);
    const rows = TABLE_QUERIES[table](this.db);
    const lines = rows.map((row) => JSON.stringify(row)).join('\n');
    writeFileSync(path, lines ? lines + '\n' : '');
    return path;
  }

  exportAll(outputDir: string, format: 'jsonl' | 'parquet'): string[] {
    return EXPORTABLE_TABLES.map((table) => this.exportTable(table, outputDir, format));
  }

  private isExportable(table: string): table is (typeof EXPORTABLE_TABLES)[number] {
    return EXPORTABLE_TABLES.includes(table as (typeof EXPORTABLE_TABLES)[number]);
  }
}
