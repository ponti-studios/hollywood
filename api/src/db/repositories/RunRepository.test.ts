import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { setupTestDb } from '../test-utils.js';
import { RunRepository } from './RunRepository.js';

describe('RunRepository', () => {
  let repo: RunRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new RunRepository(test.db);
    cleanup = test.cleanup;
  });

  afterEach(() => {
    cleanup();
  });

  it('starts a run and finds it by ID', () => {
    const runId = repo.start('variety', '{"limit": 5}');
    const found = repo.findById(runId);
    expect(found).not.toBeNull();
    expect(found!.sourceId).toBe('variety');
    expect(found!.runKind).toBe('ingest');
    expect(found!.status).toBe('running');
    expect(found!.optionsJson).toBe('{"limit": 5}');
  });

  it('starts a raw run', () => {
    const runId = repo.startRaw('normalize', { source_id: 'imdb' });
    const found = repo.findById(runId);
    expect(found).not.toBeNull();
    expect(found!.sourceId).toBe('hollywood');
    expect(found!.runKind).toBe('normalize');
    expect(found!.status).toBe('running');
  });

  it('finishes a run with succeeded status', () => {
    const runId = repo.start('deadline', '{}');
    repo.finish(runId, 'succeeded', { articles: 5 });

    const found = repo.findById(runId);
    expect(found!.status).toBe('succeeded');
    expect(found!.completedAt).not.toBeNull();
    expect(found!.summaryJson).toBe('{"articles":5}');
  });

  it('finishes a run with failed status and error text', () => {
    const runId = repo.start('tmdb', '{}');
    repo.finish(runId, 'failed', {}, 'API key missing');

    const found = repo.findById(runId);
    expect(found!.status).toBe('failed');
    expect(found!.errorText).toBe('API key missing');
  });

  it('finds runs by source', () => {
    const r1 = repo.start('variety', '{}');
    const r2 = repo.start('variety', '{"limit":1}');
    repo.start('deadline', '{}');

    const varietyRuns = repo.findBySource('variety');
    expect(varietyRuns).toHaveLength(2);
    expect(varietyRuns.map((r) => r.id).sort()).toEqual([r1, r2].sort());
  });

  it('generates unique run IDs', () => {
    const r1 = repo.start('variety', '{}');
    const r2 = repo.start('variety', '{}');
    expect(r1).not.toBe(r2);
  });
});
