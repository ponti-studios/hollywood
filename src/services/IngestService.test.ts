import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import type { Candidate } from '../enrichment/submissions/extraction.js';
import { emptyBundle, makeStableId, type EntityRow, type CreditRow } from '../ingestion/models.js';
import { ArticleRepository } from '../domain/repositories/ArticleRepository.js';
import { CreditRepository } from '../domain/repositories/CreditRepository.js';
import { EntityRepository } from '../domain/repositories/EntityRepository.js';
import { ExtractionRepository } from '../domain/repositories/ExtractionRepository.js';
import { RawRecordRepository } from '../domain/repositories/RawRecordRepository.js';
import { RunRepository } from '../domain/repositories/RunRepository.js';
import { TagRepository } from '../domain/repositories/TagRepository.js';
import { setupTestDb } from '../domain/test-utils.js';
import { IngestService } from './IngestService.js';

function makeCandidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    name: 'Jane Doe',
    bio: 'TV writer and producer',
    email: 'jane@example.com',
    phone_number: null,
    position: 'writer',
    tags: ['writer', 'tv'],
    credits: [
      { role: 'writer', type: 'tv', production: 'THE SHOW', network: null },
      { role: 'producer', type: 'tv', production: 'OTHER SHOW', network: null },
    ],
    organizations: [{ name: 'Writers Guild', type: 'union' }],
    associates: [],
    links: [{ url: 'https://imdb.com/name/nm123', type: 'IMDB' }],
    representatives: [
      {
        name: 'Agent Smith',
        title: 'agent',
        organization: 'Big Agency',
        email: 'agent@bigagency.com',
        phone_number: null,
      },
    ],
    ...overrides,
  };
}

describe('IngestService', () => {
  let svc: IngestService;
  let entityRepo: EntityRepository;
  let tagRepo: TagRepository;
  let creditRepo: CreditRepository;
  let runRepo: RunRepository;
  let rawRecordRepo: RawRecordRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    tagRepo = new TagRepository(test.db);
    creditRepo = new CreditRepository(test.db);
    runRepo = new RunRepository(test.db);
    rawRecordRepo = new RawRecordRepository(test.db);
    cleanup = test.cleanup;

    svc = new IngestService({
      runRepo,
      rawRecordRepo,
      entityRepo,
      creditRepo,
      tagRepo,
      articleRepo: new ArticleRepository(test.db),
      extractionRepo: new ExtractionRepository(test.db),
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('run tracking', () => {
    it('starts and finishes a run', () => {
      const runId = svc.startRun('variety', '{"limit": 5}');
      expect(runId).toBeTruthy();

      svc.finishRun(runId, 'succeeded', { records: 5 });
      const found = runRepo.findById(runId);
      expect(found!.status).toBe('succeeded');
    });

    it('starts a raw run', () => {
      const runId = svc.startRunRaw('normalize', { source_id: 'imdb' });
      expect(runId).toBeTruthy();
    });
  });

  describe('materializeCandidate', () => {
    it('creates entity with all related records', () => {
      const candidate = makeCandidate();
      const entityId = svc.materializeCandidate(candidate, 'test-source');

      const entity = entityRepo.findById(entityId);
      expect(entity).not.toBeNull();
      expect(entity!.name).toBe('Jane Doe');
      expect(entity!.bio).toBe('TV writer and producer');
      expect(entity!.position).toBe('writer');

      const aliases = entityRepo.findAliases(entityId);
      expect(aliases).toHaveLength(1);
      expect(aliases[0].alias).toBe('Jane Doe');

      const contacts = entityRepo.findContacts(entityId, 'email');
      expect(contacts).toHaveLength(1);
      expect(contacts[0].contactValue).toBe('jane@example.com');

      const entityTags = tagRepo.findByEntity(entityId);
      expect(entityTags).toHaveLength(2);
      expect(entityTags.map((t) => t.tag).sort()).toEqual(['tv', 'writer']);

      const links = entityRepo.findLinks(entityId);
      expect(links).toHaveLength(1);
      expect(links[0].url).toBe('https://imdb.com/name/nm123');

      const credits = creditRepo.findByPerson(entityId);
      expect(credits).toHaveLength(2);
      expect(credits.map((c) => c.role).sort()).toEqual(['producer', 'writer']);

      const showEntity = entityRepo.findByName('THE SHOW');
      expect(showEntity).toHaveLength(1);
      expect(showEntity[0].entityType).toBe('title');

      const reps = entityRepo.findRepresentatives(entityId);
      expect(reps).toHaveLength(1);
      expect(reps[0].repId).toBeTruthy();
    });

    it('is idempotent — materializing same candidate twice does not duplicate', () => {
      const candidate = makeCandidate();
      const id1 = svc.materializeCandidate(candidate, 'test');
      const id2 = svc.materializeCandidate(candidate, 'test');

      expect(id1).toBe(id2);
      expect(entityRepo.findAliases(id1)).toHaveLength(1);
      expect(tagRepo.findByEntity(id1)).toHaveLength(2);
      expect(creditRepo.findByPerson(id1)).toHaveLength(2);
    });

    it('handles candidate with minimal fields', () => {
      const minimal: Candidate = {
        name: 'Minimal Person',
        bio: 'Just a name',
        email: null,
        phone_number: null,
        position: null,
        tags: [],
        credits: [],
        organizations: [],
        associates: [],
        links: [],
        representatives: [],
      };

      const entityId = svc.materializeCandidate(minimal, 'test');
      const entity = entityRepo.findById(entityId);
      expect(entity!.name).toBe('Minimal Person');
      expect(entityRepo.findAliases(entityId)).toHaveLength(1);
      expect(tagRepo.findByEntity(entityId)).toHaveLength(0);
      expect(creditRepo.findByPerson(entityId)).toHaveLength(0);
    });

    it('handles phone number', () => {
      const candidate = makeCandidate({ phone_number: '310-555-0123' });
      const entityId = svc.materializeCandidate(candidate, 'test');
      const phones = entityRepo.findContacts(entityId, 'phone');
      expect(phones).toHaveLength(1);
      expect(phones[0].contactValue).toBe('310-555-0123');
    });
  });

  describe('applyBundle / upsertEntities', () => {
    function titleEntityRow(overrides: Partial<EntityRow> = {}): EntityRow {
      const name = overrides.name ?? 'A Title';
      return {
        entityId: makeStableId('test-title', name),
        sourceId: 'test-source',
        entityType: 'title',
        name,
        canonicalName: name.toLowerCase(),

        metadataJson: '{}',
        ...overrides,
      };
    }

    it('writes titleType through to titles.format', () => {
      const bundle = emptyBundle();
      bundle.entities.push(
        titleEntityRow({ name: 'Limited Run Show', titleType: 'Limited Series' }),
      );
      svc.applyBundle(bundle);

      const rows = entityRepo.findByName('Limited Run Show');
      expect(rows).toHaveLength(1);
      expect(rows[0].format).toBe('Limited Series');
    });

    it("falls back to 'unknown' when titleType is omitted", () => {
      const bundle = emptyBundle();
      bundle.entities.push(titleEntityRow({ name: 'No Format Show' }));
      svc.applyBundle(bundle);

      const rows = entityRepo.findByName('No Format Show');
      expect(rows).toHaveLength(1);
      expect(rows[0].format).toBe('unknown');
    });

    it('dedupes cross-source entities by canonicalName and remaps credits', () => {
      const personIdA = makeStableId('source-a', 'Jane Doe');

      // First bundle from source A
      const bundleA = emptyBundle();
      bundleA.entities.push({
        entityId: personIdA,
        sourceId: 'source-a',
        entityType: 'person',
        name: 'Jane Doe',
        canonicalName: 'jane doe',
        metadataJson: '{}',
      });
      bundleA.credits.push({
        creditId: makeStableId('credit', personIdA, 'title-1', 'writer'),
        personEntityId: personIdA,
        titleEntityId: makeStableId('source-a', 'A Show'),
        sourceId: 'source-a',
        role: 'writer',
        creditCategory: 'tv',
        metadataJson: '{}',
      });

      // Need title entities too
      const titleIdA = makeStableId('source-a', 'A Show');
      bundleA.entities.push({
        entityId: titleIdA,
        sourceId: 'source-a',
        entityType: 'title',
        name: 'A Show',
        canonicalName: 'a show',
        metadataJson: '{}',
      });

      // Apply source A
      const resultA = svc.applyBundle(bundleA);
      expect(resultA.entitiesCreated).toBe(2);
      expect(resultA.entitiesMatched).toBe(0);

      // Second bundle from source B — same person "Jane Doe", different title
      const personIdB = makeStableId('source-b', 'Jane Doe');
      const bundleB = emptyBundle();
      bundleB.entities.push({
        entityId: personIdB,
        sourceId: 'source-b',
        entityType: 'person',
        name: 'Jane Doe',
        canonicalName: 'jane doe',
        metadataJson: '{}',
      });
      const titleIdB = makeStableId('source-b', 'B Show');
      bundleB.entities.push({
        entityId: titleIdB,
        sourceId: 'source-b',
        entityType: 'title',
        name: 'B Show',
        canonicalName: 'b show',
        metadataJson: '{}',
      });
      bundleB.credits.push({
        creditId: makeStableId('credit', personIdB, titleIdB, 'producer'),
        personEntityId: personIdB,
        titleEntityId: titleIdB,
        sourceId: 'source-b',
        role: 'producer',
        creditCategory: 'tv',
        metadataJson: '{}',
      });

      // Apply source B
      const resultB = svc.applyBundle(bundleB);
      expect(resultB.entitiesMatched).toBe(1); // "jane doe" matched existing
      expect(resultB.entitiesCreated).toBe(1); // "b show" is new

      // (a) Only one people row for "jane doe"
      const people = entityRepo.findByName('Jane Doe');
      expect(people).toHaveLength(1);
      expect(people[0].entityType).toBe('person');

      // (b) B's credit attaches to A's entity id
      const credits = creditRepo.findByPerson(people[0].id);
      expect(credits).toHaveLength(2);
      expect(credits.map((c) => c.role).sort()).toEqual(['producer', 'writer']);

      // (d) Free bonus: same role + same person + same title across sources → deduped
      const bundleC = emptyBundle();
      bundleC.entities.push({
        entityId: personIdB,
        sourceId: 'source-c',
        entityType: 'person',
        name: 'Jane Doe',
        canonicalName: 'jane doe',
        metadataJson: '{}',
      });
      bundleC.entities.push({
        entityId: makeStableId('source-c', 'A Show'),
        sourceId: 'source-c',
        entityType: 'title',
        name: 'A Show',
        canonicalName: 'a show',
        metadataJson: '{}',
      });
      bundleC.credits.push({
        creditId: makeStableId('credit', personIdB, makeStableId('source-c', 'A Show'), 'writer'),
        personEntityId: personIdB,
        titleEntityId: makeStableId('source-c', 'A Show'),
        sourceId: 'source-c',
        role: 'writer',
        creditCategory: 'tv',
        metadataJson: '{}',
      });
      const resultC = svc.applyBundle(bundleC);
      expect(resultC.entitiesMatched).toBe(2); // both person + title matched

      // After remap, "writer" credit for same person + same title + same role collides → deduped
      const creditsAfterC = creditRepo.findByPerson(people[0].id);
      expect(creditsAfterC).toHaveLength(2);
    });
  });

  describe('extraction records', () => {
    it('inserts and loads raw records', () => {
      const runId = svc.startRun('test-source', '{}');
      const rawId = svc.insertExtractionRawRecord(
        runId,
        'test-source',
        '/data/test.txt',
        'hash123',
      );

      expect(rawId).toBeTruthy();
      const records = svc.loadRawRecords({ runId });
      expect(records).toHaveLength(1);
      expect(records[0].id).toBe(rawId);
    });

    it('saves extraction result without throwing', () => {
      const runId = svc.startRun('test-source', '{}');
      const rawId = svc.insertExtractionRawRecord(
        runId,
        'test-source',
        '/data/test.txt',
        'hash123',
      );
      const candidate = makeCandidate();
      svc.saveExtractionResult(
        runId,
        'test-source',
        candidate,
        'gpt-4o',
        'v1',
        '{"raw":true}',
        rawId,
      );
      expect(true).toBe(true);
    });
  });
});
