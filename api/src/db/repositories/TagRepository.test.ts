import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { setupTestDb } from '../test-utils.js';
import { EntityRepository } from './EntityRepository.js';
import { TagRepository } from './TagRepository.js';

describe('TagRepository', () => {
  let repo: TagRepository;
  let entityRepo: EntityRepository;
  let cleanup: () => void;
  let entityId: string;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new TagRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;
    entityId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice',
      canonicalName: 'alice',
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('ensures a tag exists and returns its ID', () => {
    const result = repo.ensure('writer');
    expect(result.tag).toBe('writer');
    expect(result.normalizedTag).toBe('writer');
  });

  it('ensure is idempotent — same tag returns same ID', () => {
    const r1 = repo.ensure('writer');
    const r2 = repo.ensure('Writer'); // normalized same
    expect(r1.normalizedTag).toBe(r2.normalizedTag);

    const r3 = repo.ensure('writer');
    expect(r1.id).toBe(r3.id);
  });

  it('tags an entity and finds by entity', () => {
    const tag = repo.ensure('showrunner');
    repo.tagEntity(entityId, tag.id, 'test');

    const entityTags = repo.findByEntity(entityId);
    expect(entityTags).toHaveLength(1);
    expect(entityTags[0].tag).toBe('showrunner');
  });

  it('tagEntity is idempotent', () => {
    const tag = repo.ensure('producer');
    repo.tagEntity(entityId, tag.id, 'test');
    repo.tagEntity(entityId, tag.id, 'test');

    const entityTags = repo.findByEntity(entityId);
    expect(entityTags).toHaveLength(1);
  });

  it('lists all tags', () => {
    repo.ensure('writer');
    repo.ensure('producer');
    repo.ensure('showrunner');

    const allTags = repo.findAll();
    expect(allTags).toHaveLength(3);
    expect(allTags.map((t) => t.tagName).sort()).toEqual(['producer', 'showrunner', 'writer']);
  });

  it('finds tag by ID', () => {
    const { id } = repo.ensure('director');
    const found = repo.findById(id);
    expect(found).not.toBeNull();
    expect(found!.tag).toBe('director');
  });

  it('finds tag by normalized name', () => {
    repo.ensure('executive_producer');
    const found = repo.findByNormalized('executive_producer');
    expect(found).not.toBeNull();
    expect(found!.tag).toBe('executive_producer');
  });

  it('returns empty array for entity with no tags', () => {
    const entityTags = repo.findByEntity(entityId);
    expect(entityTags).toHaveLength(0);
  });
});
