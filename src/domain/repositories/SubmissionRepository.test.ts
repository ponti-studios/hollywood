import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { setupTestDb } from '../test-utils.js';
import { ExtractionRepository } from './ExtractionRepository.js';
import { RawRecordRepository } from './RawRecordRepository.js';
import { RunRepository } from './RunRepository.js';
import { SubmissionRepository } from './SubmissionRepository.js';

describe('SubmissionRepository', () => {
  let repo: SubmissionRepository;
  let rawRecordRepo: RawRecordRepository;
  let extractionRepo: ExtractionRepository;
  let runRepo: RunRepository;
  let cleanup: () => void;
  let docId: string;
  let extractionId: string;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new SubmissionRepository(test.db);
    rawRecordRepo = new RawRecordRepository(test.db);
    extractionRepo = new ExtractionRepository(test.db);
    runRepo = new RunRepository(test.db);
    cleanup = test.cleanup;

    const runId = runRepo.start('test-source', '{}');
    docId = `doc-${Math.random().toString(36).slice(2, 8)}`;
    rawRecordRepo.insertOne({
      id: docId,
      runId,
      sourceId: 'test',
      sourceKind: 'upload',
      payloadType: 'text/plain',
      contentPath: '/data/test.txt',
      contentHash: 'abc',
      fetchedAt: new Date().toISOString(),
      metadataJson: '{}',
    });
    extractionId = extractionRepo.save({
      documentId: docId,
      schemaVersion: 'v1',
      promptVersion: 'v1',
      modelName: 'gpt-4o',
      status: 'succeeded',
      rawJson: '{}',
      resultJson: '{"name": "Jane Doe"}',
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('inserts and finds a submission', () => {
    const id = repo.insert({
      documentId: docId,
      extractionId,
      sourceId: 'test',
    });
    const found = repo.findById(id);
    expect(found).not.toBeNull();
    expect(found!.documentId).toBe(docId);
    expect(found!.extractionId).toBe(extractionId);
  });

  it('lists all submissions', () => {
    repo.insert({ documentId: docId, extractionId, sourceId: 'test' });
    repo.insert({ documentId: docId, extractionId, sourceId: 'test' });

    const all = repo.findAll();
    expect(all).toHaveLength(2);
  });

  it('finds a submission with extraction JSON', () => {
    const id = repo.insert({
      documentId: docId,
      extractionId,
      sourceId: 'test',
    });
    const withExtraction = repo.findWithExtraction(id);
    expect(withExtraction).not.toBeNull();
    expect(withExtraction!.resultJson).toBe('{"name": "Jane Doe"}');
  });

  it('lists all submissions with extractions', () => {
    repo.insert({ documentId: docId, extractionId, sourceId: 'test' });
    const all = repo.findAllWithExtractions();
    expect(all).toHaveLength(1);
    expect(all[0].resultJson).toBe('{"name": "Jane Doe"}');
  });

  it('deletes a submission', () => {
    const id = repo.insert({ documentId: docId, extractionId, sourceId: 'test' });
    expect(repo.findById(id)).not.toBeNull();
    const deleted = repo.delete(id);
    expect(deleted).toBe(1);
    expect(repo.findById(id)).toBeNull();
  });

  it('returns 0 when deleting nonexistent submission', () => {
    expect(repo.delete('nonexistent')).toBe(0);
  });

  it('returns null for missing submission', () => {
    expect(repo.findById('nonexistent')).toBeNull();
  });
});
