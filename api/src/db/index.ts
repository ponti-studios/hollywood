import BetterSqlite3 from "better-sqlite3";
import { env } from "../env.js";

let _db: BetterSqlite3.Database | null = null;

export interface DbRow {
  [key: string]: unknown;
}

export function getDb(dbPath?: string): BetterSqlite3.Database {
  if (_db) return _db;
  const path = dbPath ?? env.HOLLYWOOD_DB_PATH;
  _db = new BetterSqlite3(path);
  _db.pragma("journal_mode = DELETE");
  _db.pragma("foreign_keys = ON");
  return _db;
}

export function closeDb(): void {
  if (_db) {
    _db.close();
    _db = null;
  }
}
