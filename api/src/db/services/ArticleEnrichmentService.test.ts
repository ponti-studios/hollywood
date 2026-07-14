import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import type { ArticleMentions } from '../../ingest/article-mentions.js';
import { ArticleRepository } from '../repositories/ArticleRepository.js';
import { CompanyRelationRepository } from '../repositories/CompanyRelationRepository.js';
import { CreditRepository } from '../repositories/CreditRepository.js';
import { EntityRepository } from '../repositories/EntityRepository.js';
import { ExtractionRepository } from '../repositories/ExtractionRepository.js';
import { RawRecordRepository } from '../repositories/RawRecordRepository.js';
import { RunRepository } from '../repositories/RunRepository.js';
import { setupTestDb } from '../test-utils.js';
import { ArticleEnrichmentService } from './ArticleEnrichmentService.js';

function makeMentions(overrides: Partial<ArticleMentions> = {}): ArticleMentions {
  return {
    schemaVersion: 'v2_article_mentions',
    people: [],
    titles: [],
    companies: [],
    ...overrides,
  };
}

describe('ArticleEnrichmentService', () => {
  let svc: ArticleEnrichmentService;
  let articleRepo: ArticleRepository;
  let entityRepo: EntityRepository;
  let creditRepo: CreditRepository;
  let companyRelationRepo: CompanyRelationRepository;
  let extractionRepo: ExtractionRepository;
  let runRepo: RunRepository;
  let rawRecordRepo: RawRecordRepository;
  let cleanup: () => void;
  let runId: string;
  const articleId = 'a-001';
  const rawRecordId = 'raw-001';

  function baseParams(mentions: ArticleMentions) {
    return {
      articleId,
      rawRecordId,
      mentions,
      sourceId: 'variety',
      jobId: runId,
      promptVersion: 'v1',
      modelName: 'test-model',
      rawJson: '{}',
    };
  }

  beforeEach(() => {
    const test = setupTestDb();
    articleRepo = new ArticleRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    creditRepo = new CreditRepository(test.db);
    companyRelationRepo = new CompanyRelationRepository(test.db);
    extractionRepo = new ExtractionRepository(test.db);
    runRepo = new RunRepository(test.db);
    rawRecordRepo = new RawRecordRepository(test.db);
    cleanup = test.cleanup;
    runId = runRepo.start('variety', '{}');

    svc = new ArticleEnrichmentService({
      articleRepo,
      entityRepo,
      creditRepo,
      companyRelationRepo,
      extractionRepo,
    });

    articleRepo.upsertArticle({
      articleId,
      sourceId: 'variety',
      url: 'https://variety.com/a',
      runId,
    });
    rawRecordRepo.insertOne({
      id: rawRecordId,
      runId,
      sourceId: 'variety',
      sourceKind: 'feed',
      payloadType: 'feed_xml',
      contentPath: '/data/raw.xml',
      contentHash: 'hash',
      fetchedAt: new Date().toISOString(),
      metadataJson: '{}',
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('creates new people/titles/companies when nothing matches by canonical name', () => {
    const mentions = makeMentions({
      people: [{ name: 'Jane Doe', roleHint: 'director', relatedTo: [] }],
      titles: [{ name: 'The Crown', formatHint: 'series' }],
      companies: [{ name: 'Netflix', typeHint: 'streamer' }],
    });

    const result = svc.materializeMentions(baseParams(mentions));

    expect(result.peopleCreated).toBe(1);
    expect(result.titlesCreated).toBe(1);
    expect(result.companiesCreated).toBe(1);
    expect(result.peopleMatched).toBe(0);
    expect(entityRepo.findByCanonicalName('person', 'jane doe')).not.toBeNull();
    expect(entityRepo.findByCanonicalName('title', 'the crown')).not.toBeNull();
    expect(entityRepo.findByCanonicalName('company', 'netflix')).not.toBeNull();
  });

  it('reuses an existing entity matched by canonical name instead of creating a duplicate', () => {
    const existingId = entityRepo.upsert({
      sourceId: 'wga',
      entityType: 'person',
      name: 'Jane Doe',
      canonicalName: 'jane doe',
    });

    const mentions = makeMentions({
      people: [{ name: 'Jane Doe', roleHint: null, relatedTo: [] }],
    });
    const result = svc.materializeMentions(baseParams(mentions));

    expect(result.peopleCreated).toBe(0);
    expect(result.peopleMatched).toBe(1);
    const found = entityRepo.findByCanonicalName('person', 'jane doe');
    expect(found!.id).toBe(existingId);
  });

  it("creates a crew credit when a person's related_to targets a title", () => {
    const mentions = makeMentions({
      people: [
        {
          name: 'Jane Doe',
          roleHint: 'director',
          relatedTo: [
            { name: 'The Crown', type: 'title', relationship: 'director', character: null },
          ],
        },
      ],
      titles: [{ name: 'The Crown', formatHint: 'series' }],
    });

    const result = svc.materializeMentions(baseParams(mentions));
    expect(result.creditsCreated).toBe(1);

    const personId = entityRepo.findByCanonicalName('person', 'jane doe')!.id;
    const credits = creditRepo.findByPerson(personId);
    expect(credits).toHaveLength(1);
    expect(credits[0]!.role).toBe('director');
    expect(credits[0]!.creditCategory).toBe('crew');
    expect(credits[0]!.titleName).toBe('The Crown');
  });

  it('creates a cast credit with the character name as role when relationship is actor', () => {
    const mentions = makeMentions({
      people: [
        {
          name: 'Jane Doe',
          roleHint: 'actor',
          relatedTo: [
            {
              name: 'The Crown',
              type: 'title',
              relationship: 'actor',
              character: 'Queen Elizabeth',
            },
          ],
        },
      ],
      titles: [{ name: 'The Crown', formatHint: 'series' }],
    });

    const result = svc.materializeMentions(baseParams(mentions));
    expect(result.creditsCreated).toBe(1);

    const personId = entityRepo.findByCanonicalName('person', 'jane doe')!.id;
    const credits = creditRepo.findByPerson(personId);
    expect(credits).toHaveLength(1);
    expect(credits[0]!.role).toBe('Queen Elizabeth');
    expect(credits[0]!.creditCategory).toBe('cast');
  });

  it("creates a company_relations row when a person's related_to targets a company", () => {
    const mentions = makeMentions({
      people: [
        {
          name: 'Jane Doe',
          roleHint: null,
          relatedTo: [
            { name: 'Netflix', type: 'company', relationship: 'signed with', character: null },
          ],
        },
      ],
      companies: [{ name: 'Netflix', typeHint: 'streamer' }],
    });

    const result = svc.materializeMentions(baseParams(mentions));
    expect(result.companyRelationsCreated).toBe(1);

    const companyId = entityRepo.findByCanonicalName('company', 'netflix')!.id;
    const relations = companyRelationRepo.findByCompany(companyId);
    expect(relations).toHaveLength(1);
    expect(relations[0]!.relationship).toBe('signed with');
    expect(relations[0]!.trustState).toBe('llm_extracted');
  });

  it('links every mentioned person/title/company to the article regardless of relationships', () => {
    const mentions = makeMentions({
      people: [{ name: 'Jane Doe', roleHint: null, relatedTo: [] }],
      titles: [{ name: 'The Crown', formatHint: 'series' }],
      companies: [{ name: 'Netflix', typeHint: 'streamer' }],
    });

    const result = svc.materializeMentions(baseParams(mentions));
    expect(result.mentionsRecorded).toBe(3);

    const linked = articleRepo.findEntitiesByArticleId(articleId);
    expect(linked).toHaveLength(3);
    expect(linked.every((l) => l.relation === 'mentioned')).toBe(true);
  });

  it('does not create a structured record for a person-to-person relationship', () => {
    const mentions = makeMentions({
      people: [
        {
          name: 'Jane Doe',
          roleHint: null,
          relatedTo: [
            {
              name: 'John Smith',
              type: 'person',
              relationship: 'co-writing with',
              character: null,
            },
          ],
        },
        { name: 'John Smith', roleHint: null, relatedTo: [] },
      ],
    });

    const result = svc.materializeMentions(baseParams(mentions));
    expect(result.creditsCreated).toBe(0);
    expect(result.companyRelationsCreated).toBe(0);
    // both people still get created and linked to the article
    expect(result.peopleCreated).toBe(2);
    expect(result.mentionsRecorded).toBe(2);
  });

  it('is idempotent — materializing the same article twice does not duplicate rows', () => {
    const mentions = makeMentions({
      people: [
        {
          name: 'Jane Doe',
          roleHint: null,
          relatedTo: [
            { name: 'The Crown', type: 'title', relationship: 'director', character: null },
          ],
        },
      ],
      titles: [{ name: 'The Crown', formatHint: 'series' }],
    });

    svc.materializeMentions(baseParams(mentions));
    svc.materializeMentions(baseParams(mentions));

    const personId = entityRepo.findByCanonicalName('person', 'jane doe')!.id;
    expect(creditRepo.findByPerson(personId)).toHaveLength(1);
    expect(articleRepo.findEntitiesByArticleId(articleId)).toHaveLength(2);
    expect(extractionRepo.findByDocumentId(rawRecordId)).toHaveLength(1);
  });
});
