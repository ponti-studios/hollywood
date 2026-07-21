import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { EntityRepository } from '../domain/repositories/EntityRepository.js';
import { ExtractionRepository } from '../domain/repositories/ExtractionRepository.js';
import { RawRecordRepository } from '../domain/repositories/RawRecordRepository.js';
import { RunRepository } from '../domain/repositories/RunRepository.js';
import { SubmissionRepository } from '../domain/repositories/SubmissionRepository.js';
import { setupTestDb } from '../domain/test-utils.js';
import { SubmissionService } from './SubmissionService.js';

describe('SubmissionService', () => {
  let svc: SubmissionService;
  let submissionRepo: SubmissionRepository;
  let entityRepo: EntityRepository;
  let rawRecordRepo: RawRecordRepository;
  let extractionRepo: ExtractionRepository;
  let runRepo: RunRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    submissionRepo = new SubmissionRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    rawRecordRepo = new RawRecordRepository(test.db);
    extractionRepo = new ExtractionRepository(test.db);
    runRepo = new RunRepository(test.db);
    cleanup = test.cleanup;
    svc = new SubmissionService({ submissionRepo, entityRepo });
  });

  afterEach(() => {
    cleanup();
  });

  function createBaseData() {
    const runId = runRepo.start('test', '{}');
    const docId = `doc-${Math.random().toString(36).slice(2, 8)}`;
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
    const extractionId = extractionRepo.save({
      documentId: docId,
      schemaVersion: 'v1',
      promptVersion: 'v1',
      modelName: 'gpt-4o',
      status: 'succeeded',
      rawJson: '{}',
      resultJson: '{"name": "Jane Doe", "bio": "Writer"}',
    });
    const subId = submissionRepo.insert({
      documentId: docId,
      extractionId,
      sourceId: 'test',
    });
    return { runId, docId, extractionId, subId };
  }

  it('lists submissions', () => {
    createBaseData();
    const list = svc.list();
    expect(list).toHaveLength(1);
    expect(list[0].projectId).toBe('default');
    expect(list[0].submissionJson.name).toBe('Jane Doe');
  });

  it('deletes a submission', () => {
    const { subId } = createBaseData();
    const result = svc.delete(subId);
    expect(result.deleted).toBe(true);
    expect(submissionRepo.findById(subId)).toBeNull();
  });

  it('returns deleted=false for nonexistent submission', () => {
    const result = svc.delete('nonexistent');
    expect(result.deleted).toBe(false);
  });

  it('creates a candidate from a submission', () => {
    const { subId } = createBaseData();
    const candidate = svc.createCandidate(subId, 'writer');
    expect(candidate).not.toBeNull();
    expect(candidate!.name).toBe('Jane Doe');
    expect(candidate!.position).toBe('writer');
    expect(candidate!.status).toBe('active');
    expect(entityRepo.findById(candidate!.id)).not.toBeNull();
  });

  it('returns null when creating candidate from nonexistent submission', () => {
    const candidate = svc.createCandidate('nonexistent', 'writer');
    expect(candidate).toBeNull();
  });

  it('creates candidate idempotently from same extraction', () => {
    const { subId } = createBaseData();
    const c1 = svc.createCandidate(subId, 'writer')!;
    const c2 = svc.createCandidate(subId, 'writer')!;
    expect(c1.id).toBe(c2.id);
  });

  it('parses SubmissionPacket format with candidates array', () => {
    const runId = runRepo.start('test', '{}');
    const docId = `doc-${Math.random().toString(36).slice(2, 8)}`;
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
    const extractionId = extractionRepo.save({
      documentId: docId,
      schemaVersion: 'v1',
      promptVersion: 'v1',
      modelName: 'gpt-4o',
      status: 'succeeded',
      rawJson: '{}',
      resultJson: JSON.stringify({
        schema_version: 'v1_submission_packet',
        candidates: [{ name: 'John Writer', bio: 'Writer for TV', position: 'writer' }],
      }),
    });
    const subId = submissionRepo.insert({ documentId: docId, extractionId, sourceId: 'test' });
    const list = svc.list();
    expect(list).toHaveLength(1);
    expect(list[0].submissionJson.name).toBe('John Writer');
    expect(list[0].submissionJson.bio).toBe('Writer for TV');
  });
});
