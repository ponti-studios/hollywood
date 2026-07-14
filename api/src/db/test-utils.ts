import { readdirSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import DatabaseClass from 'better-sqlite3';
import type { Database as SqliteDb } from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';

import * as schema from './schema.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

export interface TestDb {
  sqlite: SqliteDb;
  db: ReturnType<typeof drizzle<typeof schema>>;
}

/** Create a fresh in-memory SQLite database with all tables from the Drizzle migrations. */
function createTestDb(): TestDb {
  const sqlite = new DatabaseClass(':memory:');
  sqlite.pragma('journal_mode = DELETE');
  sqlite.pragma('foreign_keys = ON');

  // Apply every Drizzle-generated migration in order
  const drizzleDir = resolve(__dirname, '../../drizzle');
  const migrationFiles = readdirSync(drizzleDir)
    .filter((f) => f.endsWith('.sql'))
    .sort();
  for (const file of migrationFiles) {
    const sql = readFileSync(resolve(drizzleDir, file), 'utf-8');
    const statements = sql.split('--> statement-breakpoint');
    for (const stmt of statements) {
      const trimmed = stmt.trim();
      if (trimmed) sqlite.exec(trimmed);
    }
  }

  const db = drizzle(sqlite, { schema });
  return { sqlite, db };
}

/** Per-test helper: wraps createTestDb + makes cleanup easy */
export function setupTestDb() {
  const { sqlite, db } = createTestDb();

  return {
    db,
    /** Close the in-memory database. Call in afterEach/teardown. */
    cleanup() {
      sqlite.close();
    },
  };
}
