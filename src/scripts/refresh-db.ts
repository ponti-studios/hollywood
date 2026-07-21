import { existsSync, rmSync } from 'node:fs';

import DatabaseClass from 'better-sqlite3';

import { closeDb } from '../db.js';
import { applyMigrations } from '../domain/migrate.js';
import { env } from '../env.js';

const DEFAULT_LIMIT = 3;

function parseLimit(): number {
  const arg = process.argv.find((a) => a.startsWith('--limit='));
  if (!arg) return DEFAULT_LIMIT;
  const value = Number(arg.slice('--limit='.length));
  return Number.isFinite(value) ? value : DEFAULT_LIMIT;
}

/**
 * Recreates the dev SQLite database from the Drizzle migrations, then runs an
 * ingest across every registered source. Destructive by design — this is a
 * dev-only reset, not a migration tool for a database with data worth keeping.
 *
 * Defaults to a small per-source limit (enough to prove the pipeline works
 * end to end) rather than a mass ingest — the WGA adapter in particular
 * defaults to crawling every a-z prefix, which is a long, heavy crawl.
 * Pass --limit=N to override, or --limit=0 for an unbounded full ingest.
 */
async function main(): Promise<void> {
  const dbPath = env.HOLLYWOOD_DB_PATH;
  const limit = parseLimit();

  console.log(`Deleting existing database at ${dbPath}`);
  for (const suffix of ['', '-wal', '-shm']) {
    const path = `${dbPath}${suffix}`;
    if (existsSync(path)) rmSync(path);
  }

  console.log('Applying migrations to a fresh database...');
  const sqlite = new DatabaseClass(dbPath);
  sqlite.pragma('journal_mode = DELETE');
  sqlite.pragma('foreign_keys = ON');
  applyMigrations(sqlite);
  sqlite.close();

  // Deferred to a dynamic import: ingestion/flows.js constructs a
  // module-level IngestService as soon as it's loaded, which opens (and
  // caches) a DB connection immediately. A static import at the top of this
  // file would open that connection against the *old* database, before the
  // file above was deleted and recreated.
  const { registerAllAdapters } = await import('../ingestion/adapters/index.js');
  const { runIngestGroup } = await import('../ingestion/flows.js');

  registerAllAdapters();

  console.log(
    limit ? `Running ingest across all sources (limit=${limit})...` : 'Running full ingest across all sources...',
  );
  const summaries = await runIngestGroup('all', { fullText: true, limit: limit || undefined });
  for (const summary of summaries) {
    console.log(
      `  ${summary.sourceId}: ${summary.status} — ` +
        `${summary.rawRecords} raw records, ` +
        `${summary.entitiesCreated} entities created, ` +
        `${summary.entitiesMatched} entities matched`,
    );
    if (summary.error) console.log(`    error: ${summary.error}`);
  }

  closeDb();

  const failed = summaries.filter((s) => s.status === 'failed');
  if (failed.length > 0) {
    console.log(`Done, with ${failed.length} source(s) failed.`);
    process.exit(1);
  }
  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
