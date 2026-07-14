import { randomUUID } from 'node:crypto';

import { eq } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';

import { getDrizzle } from '../index.js';
import { runs } from '../schema.js';
import * as schema from '../schema.js';

export type RunStatus = 'running' | 'succeeded' | 'failed';

type Db = BetterSQLite3Database<typeof schema>;

export class RunRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Start a new ingest run. Returns the run ID. */
  start(sourceId: string, optionsJson: string): string {
    const runId = randomUUID();
    const now = new Date().toISOString();
    this.db
      .insert(runs)
      .values({
        id: runId,
        sourceId,
        runKind: 'ingest',
        status: 'running',
        startedAt: now,
        optionsJson,
      })
      .run();
    return runId;
  }

  /** Start a raw run (not tied to a specific source). */
  startRaw(runKind: string, metadata: Record<string, unknown>): string {
    const runId = randomUUID();
    const now = new Date().toISOString();
    const metaJson = JSON.stringify(metadata);
    this.db
      .insert(runs)
      .values({
        id: runId,
        sourceId: 'hollywood',
        runKind,
        status: 'running',
        startedAt: now,
        optionsJson: metaJson,
      })
      .run();
    return runId;
  }

  /** Mark a run as finished with the given status and summary. */
  finish(
    runId: string,
    status: RunStatus,
    summary: object,
    errorText?: string,
  ): void {
    this.db
      .update(runs)
      .set({
        status,
        completedAt: new Date().toISOString(),
        summaryJson: JSON.stringify(summary),
        errorText: errorText ?? null,
      })
      .where(eq(runs.id, runId))
      .run();
  }

  /** Find a run by ID. */
  findById(runId: string) {
    return this.db.select().from(runs).where(eq(runs.id, runId)).get() ?? null;
  }

  /** Find all runs for a given source, newest first. */
  findBySource(sourceId: string) {
    return this.db
      .select()
      .from(runs)
      .where(eq(runs.sourceId, sourceId))
      .orderBy(runs.startedAt)
      .all();
  }
}
