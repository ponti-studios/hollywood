import DatabaseClass from 'better-sqlite3';
import type { Database as SqliteDb } from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';

import { applyMigrations } from './migrate.js';
import * as schema from './schema.js';

export interface TestDb {
  sqlite: SqliteDb;
  db: ReturnType<typeof drizzle<typeof schema>>;
}

/** Create a fresh in-memory SQLite database with all tables from the Drizzle migrations. */
function createTestDb(): TestDb {
  const sqlite = new DatabaseClass(':memory:');
  sqlite.pragma('journal_mode = DELETE');
  sqlite.pragma('foreign_keys = ON');

  applyMigrations(sqlite);

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
