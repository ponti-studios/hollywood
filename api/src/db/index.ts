import BetterSqlite3 from "better-sqlite3";
import { homedir } from "os";
import { resolve } from "path";

let _db: BetterSqlite3.Database | null = null;

export interface DbRow {
  [key: string]: unknown;
}

function defaultDbPath(): string {
  return resolve(homedir(), ".hominem", "hollywood.db");
}

export function getDb(dbPath?: string): BetterSqlite3.Database {
  if (_db) return _db;
  const path = dbPath ?? process.env["HOLLYWOOD_DB_PATH"] ?? defaultDbPath();
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
