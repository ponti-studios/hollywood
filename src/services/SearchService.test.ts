import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { CreditRepository } from '../domain/repositories/CreditRepository.js';
import { EntityRepository } from '../domain/repositories/EntityRepository.js';
import { setupTestDb } from '../domain/test-utils.js';
import { SearchService } from './SearchService.js';

describe('SearchService', () => {
  let svc: SearchService;
  let entityRepo: EntityRepository;
  let creditRepo: CreditRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    creditRepo = new CreditRepository(test.db);
    cleanup = test.cleanup;
    svc = new SearchService({ entityRepo, creditRepo });
  });

  afterEach(() => {
    cleanup();
  });

  it('searches entities by name', () => {
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alyson Fouse',
      canonicalName: 'alyson fouse',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'John Smith',
      canonicalName: 'john smith',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: "ALYSON'S SHOW",
      canonicalName: "alyson's show",
    });

    const results = svc.search('Alyson');
    expect(results.total).toBe(2);
    expect(results.entities.map((e) => e.name).sort()).toEqual(["ALYSON'S SHOW", 'Alyson Fouse']);
  });

  it('returns empty results for no match', () => {
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alyson Fouse',
      canonicalName: 'alyson fouse',
    });

    const results = svc.search('ZZZZZ');
    expect(results.total).toBe(0);
    expect(results.entities).toHaveLength(0);
  });

  it('respects limit', () => {
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice A',
      canonicalName: 'alice a',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice B',
      canonicalName: 'alice b',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice C',
      canonicalName: 'alice c',
    });

    const results = svc.search('Alice', 2);
    expect(results.total).toBe(3);
    expect(results.entities).toHaveLength(2);
  });

  it('includes credits in search results', () => {
    const personId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alyson Fouse',
      canonicalName: 'alyson fouse',
    });
    const titleId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
    });
    creditRepo.upsert({ personId, titleId, sourceId: 'test', role: 'writer' });

    const results = svc.search('Alyson');
    expect(results.entities[0].credits).toHaveLength(1);
    expect(results.entities[0].credits[0].production).toBe('THE SHOW');
  });
});
