import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { setupTestDb } from '../test-utils.js';
import { CompanyRelationRepository } from './CompanyRelationRepository.js';
import { EntityRepository } from './EntityRepository.js';

describe('CompanyRelationRepository', () => {
  let repo: CompanyRelationRepository;
  let entityRepo: EntityRepository;
  let cleanup: () => void;
  let companyId: string;
  let titleId: string;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new CompanyRelationRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;

    companyId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'company',
      name: 'Netflix',
      canonicalName: 'netflix',
      companyType: 'streamer',
    });
    titleId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'The Crown',
      canonicalName: 'the crown',
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('creates a company relation row', () => {
    const id = repo.upsert({
      companyAId: companyId,
      entityType: 'title',
      entityId: titleId,
      relationship: 'producing',
      sourceId: 'test',
    });

    expect(id).toBeTruthy();
    const rows = repo.findByCompany(companyId);
    expect(rows).toHaveLength(1);
    expect(rows[0]!.entityId).toBe(titleId);
    expect(rows[0]!.relationship).toBe('producing');
    expect(rows[0]!.trustState).toBe('machine_extracted');
  });

  it('is idempotent for the same (companyAId, entityId, relationship)', () => {
    const id1 = repo.upsert({
      companyAId: companyId,
      entityType: 'title',
      entityId: titleId,
      relationship: 'producing',
      sourceId: 'test',
    });
    const id2 = repo.upsert({
      companyAId: companyId,
      entityType: 'title',
      entityId: titleId,
      relationship: 'producing',
      sourceId: 'test',
    });

    expect(id1).toBe(id2);
    expect(repo.findByCompany(companyId)).toHaveLength(1);
  });

  it('allows a different relationship for the same pair as a separate row', () => {
    repo.upsert({
      companyAId: companyId,
      entityType: 'title',
      entityId: titleId,
      relationship: 'producing',
      sourceId: 'test',
    });
    repo.upsert({
      companyAId: companyId,
      entityType: 'title',
      entityId: titleId,
      relationship: 'distributing',
      sourceId: 'test',
    });

    expect(repo.findByCompany(companyId)).toHaveLength(2);
  });

  it('accepts a custom trustState', () => {
    repo.upsert({
      companyAId: companyId,
      entityType: 'title',
      entityId: titleId,
      relationship: 'producing',
      sourceId: 'test',
      trustState: 'llm_extracted',
    });
    expect(repo.findByCompany(companyId)[0]!.trustState).toBe('llm_extracted');
  });
});
