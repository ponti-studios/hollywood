import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { EntityRepository } from '../domain/repositories/EntityRepository.js';
import { setupTestDb } from '../domain/test-utils.js';
import { ProjectService } from './ProjectService.js';

describe('ProjectService', () => {
  let svc: ProjectService;
  let entityRepo: EntityRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;
    svc = new ProjectService({ entityRepo });
  });

  afterEach(() => {
    cleanup();
  });

  it('lists projects (titles)', () => {
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
      metadataJson: '{"genres":["drama"]}',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'OTHER SHOW',
      canonicalName: 'other show',
    });
    entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice',
      canonicalName: 'alice',
    });

    const projects = svc.list();
    expect(projects).toHaveLength(2);
    expect(projects.map((p) => p.title).sort()).toEqual(['OTHER SHOW', 'THE SHOW']);
  });

  it('gets a single project by ID', () => {
    const id = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'title',
      name: 'THE SHOW',
      canonicalName: 'the show',
      titleType: 'tv',
      metadataJson: '{"genres":["comedy"],"season":3}',
    });

    const project = svc.get(id);
    expect(project).not.toBeNull();
    expect(project!.title).toBe('THE SHOW');
    expect(project!.format).toBe('tv');
    expect(project!.genres).toEqual(['comedy']);
    expect(project!.season).toBe(3);
  });

  it('returns null for nonexistent project', () => {
    expect(svc.get('nonexistent')).toBeNull();
  });

  it('returns null when entity is not a title', () => {
    const id = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Alice',
      canonicalName: 'alice',
    });
    expect(svc.get(id)).toBeNull();
  });

  it('creates a project with stable ID', () => {
    const project = svc.create({
      title: 'New Show',
      format: 'tv',
      genres: ['drama'],
      season: 1,
    });

    expect(project.title).toBe('New Show');
    expect(project.format).toBe('tv');
    expect(project.genres).toEqual(['drama']);
    expect(project.season).toBe(1);

    // Same name produces same ID
    const project2 = svc.create({ title: 'New Show' });
    expect(project2.id).toBe(project.id);
  });

  it('updates a project', () => {
    const created = svc.create({ title: 'Old Show', format: 'tv' });
    const updated = svc.update(created.id, { title: 'New Show', genres: ['comedy'], season: 2 });

    expect(updated).not.toBeNull();
    expect(updated!.title).toBe('New Show');
    expect(updated!.genres).toEqual(['comedy']);
    expect(updated!.season).toBe(2);
  });

  it('returns null when updating nonexistent project', () => {
    const result = svc.update('nonexistent', { title: 'New Name' });
    expect(result).toBeNull();
  });

  it('provides defaults for metadata fields', () => {
    const created = svc.create({ title: 'Minimal Show' });
    expect(created.season).toBe(1);
    expect(created.genres).toEqual([]);
    expect(created.posterLink).toBeNull();
  });
});
