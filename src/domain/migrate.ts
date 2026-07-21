import { readdirSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import type { Database as SqliteDb } from 'better-sqlite3';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Apply every Drizzle-generated migration file, in order, to a SQLite connection. */
export function applyMigrations(sqlite: SqliteDb): void {
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
}
