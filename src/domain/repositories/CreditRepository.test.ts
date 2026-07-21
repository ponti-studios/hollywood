import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { setupTestDb } from '../test-utils.js';
import { CreditRepository } from './CreditRepository.js';
import { EntityRepository } from './EntityRepository.js';

describe('CreditRepository', () => {
  let repo: CreditRepository;
  let entityRepo: EntityRepository;
  let cleanup: () => void;
  let personId: string;
  let titleId: string;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new CreditRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;

    personId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Jane Writer',
      canonicalName: 'jane writer',
    });
    titleId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('upserts a credit and finds by person', () => {
    const creditId = repo.upsert({
      personId,
      titleId,
      sourceId: 'test',
      role: 'writer',
      creditCategory: 'crew',
    });

    const personCredits = repo.findByPerson(personId);
    expect(personCredits).toHaveLength(1);
    expect(personCredits[0].role).toBe('writer');
    expect(personCredits[0].titleName).toBe('THE SHOW');
    expect(personCredits[0].id).toBe(creditId);
  });

  it('finds by title', () => {
    repo.upsert({ personId, titleId, sourceId: 'test', role: 'writer' });

    const titleCredits = repo.findByTitle(titleId);
    expect(titleCredits).toHaveLength(1);
    expect(titleCredits[0].role).toBe('writer');
    expect(titleCredits[0].personName).toBe('Jane Writer');
  });

  it('upsert is idempotent', () => {
    const c1 = repo.upsert({ personId, titleId, sourceId: 'test', role: 'writer' });
    const c2 = repo.upsert({ personId, titleId, sourceId: 'test', role: 'writer' });
    expect(c1).toBe(c2);
    expect(repo.findByPerson(personId)).toHaveLength(1);
  });

  it('same person can have multiple credits on different titles', () => {
    const title2Id = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'OTHER SHOW',
      canonicalName: 'other show',
    });

    repo.upsert({ personId, titleId, sourceId: 'test', role: 'writer' });
    repo.upsert({ personId, titleId: title2Id, sourceId: 'test', role: 'producer' });

    const personCredits = repo.findByPerson(personId);
    expect(personCredits).toHaveLength(2);
  });

  it('handles billing and company', () => {
    const companyId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'company',
      name: 'Studio X',
      canonicalName: 'studio x',
    });

    repo.upsert({
      personId,
      titleId,
      companyId,
      sourceId: 'test',
      role: 'executive producer',
      creditCategory: 'production',
      billing: 1,
    });

    const credits = repo.findByPerson(personId);
    expect(credits[0].creditCategory).toBe('production');
  });

  it('returns empty array for person with no credits', () => {
    const otherPerson = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Nobody',
      canonicalName: 'nobody',
    });
    expect(repo.findByPerson(otherPerson)).toHaveLength(0);
  });

  it('stores and returns metadataJson', () => {
    repo.upsert({
      personId,
      titleId,
      sourceId: 'test',
      role: 'actor',
      metadataJson: JSON.stringify({ characters: 'Detective Reyes' }),
    });

    const personCredits = repo.findByPerson(personId);
    expect(personCredits[0].metadataJson).toBe(JSON.stringify({ characters: 'Detective Reyes' }));
  });

  it('defaults metadataJson to an empty object when omitted', () => {
    repo.upsert({ personId, titleId, sourceId: 'test', role: 'writer' });

    const personCredits = repo.findByPerson(personId);
    expect(personCredits[0].metadataJson).toBe('{}');
  });
});
