import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { CreditRepository } from '../repositories/CreditRepository.js';
import { EntityRepository } from '../repositories/EntityRepository.js';
import { TagRepository } from '../repositories/TagRepository.js';
import { setupTestDb } from '../test-utils.js';
import { CandidateService } from './CandidateService.js';

describe('CandidateService', () => {
  let svc: CandidateService;
  let entityRepo: EntityRepository;
  let creditRepo: CreditRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    creditRepo = new CreditRepository(test.db);
    cleanup = test.cleanup;
    svc = new CandidateService({
      entityRepo,
      creditRepo,
      tagRepo: new TagRepository(test.db),
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('lists candidates (persons)', () => {
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice',
      canonicalName: 'alice',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Bob',
      canonicalName: 'bob',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
    });

    const candidates = svc.list();
    expect(candidates).toHaveLength(2);
    expect(candidates.map((c) => c.name).sort()).toEqual(['Alice', 'Bob']);
  });

  it('gets a single candidate by ID', () => {
    const id = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Charlie',
      canonicalName: 'charlie',
      bio: 'The bio',
      position: 'writer',
    });

    const candidate = svc.get(id);
    expect(candidate).not.toBeNull();
    expect(candidate!.name).toBe('Charlie');
    expect(candidate!.agencyBio).toBe('The bio');
    expect(candidate!.position).toBe('writer');
    expect(candidate!.status).toBe('active');
  });

  it('returns null for nonexistent candidate', () => {
    expect(svc.get('nonexistent')).toBeNull();
  });

  it('returns null when entity is not a person', () => {
    const id = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
    });
    expect(svc.get(id)).toBeNull();
  });

  it('creates candidates with stable IDs from hollywood-api source', () => {
    const results = svc.create([
      { name: 'Jane Doe', agencyBio: 'Writer', position: 'writer', tags: ['tv'] },
      { name: 'John Smith', position: 'producer' },
    ]);

    expect(results).toHaveLength(2);
    expect(results[0].name).toBe('Jane Doe');
    expect(results[0].agencyBio).toBe('Writer');
    expect(results[0].position).toBe('writer');
    expect(results[0].tags).toHaveLength(1);
    expect(results[0].tags[0].label).toBe('tv');

    // Stable IDs — same input creates same ID
    const results2 = svc.create([{ name: 'Jane Doe', position: 'writer' }]);
    expect(results2[0].id).toBe(results[0].id);
  });

  it('updates a candidate', () => {
    const [created] = svc.create([{ name: 'Alice', agencyBio: 'Old bio', position: 'writer' }]);

    const updated = svc.update(created.id, { name: 'Alice Smith', agencyBio: 'New bio' });
    expect(updated).not.toBeNull();
    expect(updated!.name).toBe('Alice Smith');
    expect(updated!.agencyBio).toBe('New bio');
  });

  it('returns null when updating nonexistent candidate', () => {
    const result = svc.update('nonexistent', { name: 'New Name' });
    expect(result).toBeNull();
  });

  it('deletes a candidate', () => {
    const [created] = svc.create([{ name: 'To Delete', position: 'writer' }]);
    expect(svc.delete(created.id)).toBe(true);
    expect(svc.get(created.id)).toBeNull();
  });

  it('returns false when deleting nonexistent candidate', () => {
    expect(svc.delete('nonexistent')).toBe(false);
  });

  it('returns total count', () => {
    expect(svc.totalCount()).toBe(0);
    svc.create([{ name: 'Alice', position: 'writer' }]);
    expect(svc.totalCount()).toBe(1);
    svc.create([{ name: 'Bob', position: 'producer' }]);
    expect(svc.totalCount()).toBe(2);
  });

  it('enriches candidates with credits, tags, emails', () => {
    const [created] = svc.create([{ name: 'Jane', position: 'writer', tags: ['showrunner'] }]);

    // Add a credit and contact to test enrichment
    const titleId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
    });
    creditRepo.upsert({ personId: created.id, titleId, sourceId: 'test', role: 'writer' });
    entityRepo.addContact(created.id, 'test', 'email', 'jane@example.com');

    const candidate = svc.get(created.id);
    expect(candidate!.credits).toHaveLength(1);
    expect(candidate!.credits[0].production).toBe('THE SHOW');
    expect(candidate!.emails).toHaveLength(1);
    expect(candidate!.emails[0].address).toBe('jane@example.com');
    expect(candidate!.tags).toHaveLength(1);
    expect(candidate!.tags[0].label).toBe('showrunner');
  });
});
