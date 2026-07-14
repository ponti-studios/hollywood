import BetterSqlite3 from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';

import { env } from '../env.js';
import * as schema from './schema.js';

let _db: BetterSqlite3.Database | null = null;
let _drizzle: ReturnType<typeof createDrizzle> | null = null;

function createDrizzle(sqlite: BetterSqlite3.Database) {
  return drizzle(sqlite, { schema });
}

export function getDb(dbPath?: string): BetterSqlite3.Database {
  if (_db) return _db;
  const path = dbPath ?? env.HOLLYWOOD_DB_PATH;
  _db = new BetterSqlite3(path);
  _db.pragma('journal_mode = DELETE');
  _db.pragma('foreign_keys = ON');
  return _db;
}

export function getDrizzle(dbPath?: string) {
  if (_drizzle) return _drizzle;
  const sqlite = getDb(dbPath);
  return (_drizzle = createDrizzle(sqlite));
}

export function closeDb(): void {
  _drizzle = null;
  if (_db) {
    _db.close();
    _db = null;
  }
}
