import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { setupTestDb } from '../test-utils.js';
import { ArticleRepository, type ArticleFields } from './ArticleRepository.js';
import { EntityRepository } from './EntityRepository.js';
import { ExtractionRepository } from './ExtractionRepository.js';
import { RawRecordRepository } from './RawRecordRepository.js';
import { RunRepository } from './RunRepository.js';

describe('ArticleRepository', () => {
  let repo: ArticleRepository;
  let runRepo: RunRepository;
  let entityRepo: EntityRepository;
  let rawRecordRepo: RawRecordRepository;
  let extractionRepo: ExtractionRepository;
  let cleanup: () => void;
  let runId: string;

  function makeArticle(overrides: Partial<ArticleFields> = {}): ArticleFields {
    return {
      articleId: `article-${Math.random().toString(36).slice(2, 8)}`,
      sourceId: 'variety',
      url: 'https://variety.com/article',

      runId,
      ...overrides,
    };
  }

  function makeRawRecord(id: string): void {
    rawRecordRepo.insertOne({
      id,
      runId,
      sourceId: 'variety',
      sourceKind: 'feed',
      payloadType: 'feed_xml',
      contentPath: `/data/${id}.xml`,
      contentHash: id,
      fetchedAt: new Date().toISOString(),
      metadataJson: '{}',
    });
  }

  beforeEach(() => {
    const test = setupTestDb();
    repo = new ArticleRepository(test.db);
    runRepo = new RunRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    rawRecordRepo = new RawRecordRepository(test.db);
    extractionRepo = new ExtractionRepository(test.db);
    cleanup = test.cleanup;
    runId = runRepo.start('variety', '{}');
  });

  afterEach(() => {
    cleanup();
  });

  it('inserts and finds an article', () => {
    const article = makeArticle({ articleId: 'a-001', title: 'Breaking News' });
    repo.upsertArticle(article);
    const found = repo.findArticleById('a-001');
    expect(found).not.toBeNull();
    expect(found!.title).toBe('Breaking News');
    expect(found!.sourceId).toBe('variety');
  });

  it('upsert replaces existing article', () => {
    repo.upsertArticle(makeArticle({ articleId: 'a-001', title: 'Old Title' }));
    repo.upsertArticle(makeArticle({ articleId: 'a-001', title: 'New Title' }));
    const found = repo.findArticleById('a-001');
    expect(found!.title).toBe('New Title');
  });

  it('inserts and finds article content', () => {
    const article = makeArticle({ articleId: 'a-001' });
    repo.upsertArticle(article);
    repo.upsertContent({
      contentId: 'c-001',
      articleId: 'a-001',
      sourceId: 'variety',
      contentKind: 'full_text',
      text: 'Article body text here',
      contentHash: 'hash123',
    });

    const content = repo.findContentByArticleId('a-001');
    expect(content).toHaveLength(1);
    expect(content[0].text).toBe('Article body text here');
  });

  it('links entity to article', () => {
    const article = makeArticle({ articleId: 'a-001' });
    repo.upsertArticle(article);
    const entityId = entityRepo.upsert({
      sourceId: 'test',
      entityType: 'person',
      name: 'Jane',
      canonicalName: 'jane',
    });

    repo.linkEntity({
      articleEntityId: 'ae-001',
      articleId: 'a-001',
      entityId,
      sourceId: 'variety',
      relation: 'mentioned',
    });

    const entities = repo.findEntitiesByArticleId('a-001');
    expect(entities).toHaveLength(1);
    expect(entities[0].entityId).toBe(entityId);
  });

  it('finds articles by source', () => {
    repo.upsertArticle(makeArticle({ articleId: 'a-001', sourceId: 'variety' }));
    repo.upsertArticle(makeArticle({ articleId: 'a-002', sourceId: 'deadline' }));
    repo.upsertArticle(makeArticle({ articleId: 'a-003', sourceId: 'variety' }));

    const varietyArticles = repo.findBySource('variety');
    expect(varietyArticles).toHaveLength(2);
  });

  it('batches article upserts', () => {
    repo.upsertArticles([makeArticle({ articleId: 'a-001' }), makeArticle({ articleId: 'a-002' })]);

    expect(repo.findArticleById('a-001')).not.toBeNull();
    expect(repo.findArticleById('a-002')).not.toBeNull();
  });

  it('returns null for missing article', () => {
    expect(repo.findArticleById('nonexistent')).toBeNull();
  });

  describe('findUnextractedContent', () => {
    it('returns an article that only has feed_description', () => {
      makeRawRecord('raw-1');
      repo.upsertArticle(makeArticle({ articleId: 'a-001' }));
      repo.upsertContent({
        contentId: 'c-desc',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_description',
        text: 'A short summary.',
        rawRecordId: 'raw-1',
        contentHash: 'h1',
      });

      const rows = repo.findUnextractedContent('v1_article_mentions', 10);
      expect(rows).toHaveLength(1);
      expect(rows[0]!.articleId).toBe('a-001');
      expect(rows[0]!.text).toBe('A short summary.');
      expect(rows[0]!.rawRecordId).toBe('raw-1');
    });

    it('prefers feed_content over feed_description for the same article', () => {
      makeRawRecord('raw-1');
      repo.upsertArticle(makeArticle({ articleId: 'a-001' }));
      repo.upsertContent({
        contentId: 'c-desc',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_description',
        text: 'A short summary.',
        rawRecordId: 'raw-1',
        contentHash: 'h1',
      });
      repo.upsertContent({
        contentId: 'c-full',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_content',
        text: 'The full article body.',
        rawRecordId: 'raw-1',
        contentHash: 'h2',
      });

      const rows = repo.findUnextractedContent('v1_article_mentions', 10);
      expect(rows).toHaveLength(1);
      expect(rows[0]!.text).toBe('The full article body.');
    });

    it('prefers page_extract over feed_content', () => {
      makeRawRecord('raw-1');
      makeRawRecord('raw-2');
      repo.upsertArticle(makeArticle({ articleId: 'a-001' }));
      repo.upsertContent({
        contentId: 'c-full',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_content',
        text: 'The full article body.',
        rawRecordId: 'raw-1',
        contentHash: 'h1',
      });
      repo.upsertContent({
        contentId: 'c-page',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'page_extract',
        text: 'The richest scraped page text.',
        rawRecordId: 'raw-2',
        contentHash: 'h2',
      });

      const rows = repo.findUnextractedContent('v1_article_mentions', 10);
      expect(rows).toHaveLength(1);
      expect(rows[0]!.text).toBe('The richest scraped page text.');
    });

    it('excludes an article already extracted under the same schema version', () => {
      makeRawRecord('raw-1');
      repo.upsertArticle(makeArticle({ articleId: 'a-001' }));
      repo.upsertContent({
        contentId: 'c-desc',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_description',
        text: 'A short summary.',
        rawRecordId: 'raw-1',
        contentHash: 'h1',
      });
      extractionRepo.save({
        documentId: 'raw-1',
        jobId: runId,
        schemaVersion: 'v1_article_mentions',
        promptVersion: 'v1',
        modelName: 'test-model',
        status: 'succeeded',
        rawJson: '{}',
        resultJson: '{}',
      });

      expect(repo.findUnextractedContent('v1_article_mentions', 10)).toHaveLength(0);
    });

    it('still returns an article extracted under a different schema version', () => {
      makeRawRecord('raw-1');
      repo.upsertArticle(makeArticle({ articleId: 'a-001' }));
      repo.upsertContent({
        contentId: 'c-desc',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_description',
        text: 'A short summary.',
        rawRecordId: 'raw-1',
        contentHash: 'h1',
      });
      extractionRepo.save({
        documentId: 'raw-1',
        jobId: runId,
        schemaVersion: 'v0_other_schema',
        promptVersion: 'v1',
        modelName: 'test-model',
        status: 'succeeded',
        rawJson: '{}',
        resultJson: '{}',
      });

      expect(repo.findUnextractedContent('v1_article_mentions', 10)).toHaveLength(1);
    });

    it("skips content rows with no rawRecordId (can't record provenance)", () => {
      repo.upsertArticle(makeArticle({ articleId: 'a-001' }));
      repo.upsertContent({
        contentId: 'c-desc',
        articleId: 'a-001',
        sourceId: 'variety',
        contentKind: 'feed_description',
        text: 'A short summary.',
        contentHash: 'h1',
      });

      expect(repo.findUnextractedContent('v1_article_mentions', 10)).toHaveLength(0);
    });

    it('respects the limit', () => {
      for (const n of [1, 2, 3]) {
        makeRawRecord(`raw-${n}`);
        repo.upsertArticle(makeArticle({ articleId: `a-00${n}` }));
        repo.upsertContent({
          contentId: `c-${n}`,
          articleId: `a-00${n}`,
          sourceId: 'variety',
          contentKind: 'feed_description',
          text: `Summary ${n}`,
          rawRecordId: `raw-${n}`,
          contentHash: `h${n}`,
        });
      }

      expect(repo.findUnextractedContent('v1_article_mentions', 2)).toHaveLength(2);
    });
  });
});
