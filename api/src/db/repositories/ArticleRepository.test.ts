import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { setupTestDb } from "../test-utils.js";
import { ArticleRepository, type ArticleFields } from "./ArticleRepository.js";
import { RunRepository } from "./RunRepository.js";
import { EntityRepository } from "./EntityRepository.js";

describe("ArticleRepository", () => {
  let repo: ArticleRepository;
  let runRepo: RunRepository;
  let entityRepo: EntityRepository;
  let cleanup: () => void;
  let runId: string;

  function makeArticle(overrides: Partial<ArticleFields> = {}): ArticleFields {
    return {
      articleId: `article-${Math.random().toString(36).slice(2, 8)}`,
      sourceId: "variety",
      url: "https://variety.com/article",
      licenseClass: "web_copyright",
      runId,
      ...overrides,
    };
  }

  beforeEach(() => {
    const test = setupTestDb();
    repo = new ArticleRepository(test.db);
    runRepo = new RunRepository(test.db);
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;
    runId = runRepo.start("variety", "{}");
  });

  afterEach(() => {
    cleanup();
  });

  it("inserts and finds an article", () => {
    const article = makeArticle({ articleId: "a-001", title: "Breaking News" });
    repo.upsertArticle(article);
    const found = repo.findArticleById("a-001");
    expect(found).not.toBeNull();
    expect(found!.title).toBe("Breaking News");
    expect(found!.sourceId).toBe("variety");
  });

  it("upsert replaces existing article", () => {
    repo.upsertArticle(makeArticle({ articleId: "a-001", title: "Old Title" }));
    repo.upsertArticle(makeArticle({ articleId: "a-001", title: "New Title" }));
    const found = repo.findArticleById("a-001");
    expect(found!.title).toBe("New Title");
  });

  it("inserts and finds article content", () => {
    const article = makeArticle({ articleId: "a-001" });
    repo.upsertArticle(article);
    repo.upsertContent({
      contentId: "c-001",
      articleId: "a-001",
      sourceId: "variety",
      contentKind: "full_text",
      text: "Article body text here",
      contentHash: "hash123",
      licenseClass: "web_copyright",
    });

    const content = repo.findContentByArticleId("a-001");
    expect(content).toHaveLength(1);
    expect(content[0].text).toBe("Article body text here");
  });

  it("links entity to article", () => {
    const article = makeArticle({ articleId: "a-001" });
    repo.upsertArticle(article);
    const entityId = entityRepo.upsert({
      sourceId: "test", entityType: "person", name: "Jane",
      canonicalName: "jane", licenseClass: "public",
    });

    repo.linkEntity({
      articleEntityId: "ae-001",
      articleId: "a-001",
      entityId,
      sourceId: "variety",
      relation: "mentioned",
    });

    const entities = repo.findEntitiesByArticleId("a-001");
    expect(entities).toHaveLength(1);
    expect(entities[0].entityId).toBe(entityId);
  });

  it("finds articles by source", () => {
    repo.upsertArticle(makeArticle({ articleId: "a-001", sourceId: "variety" }));
    repo.upsertArticle(makeArticle({ articleId: "a-002", sourceId: "deadline" }));
    repo.upsertArticle(makeArticle({ articleId: "a-003", sourceId: "variety" }));

    const varietyArticles = repo.findBySource("variety");
    expect(varietyArticles).toHaveLength(2);
  });

  it("batches article upserts", () => {
    repo.upsertArticles([
      makeArticle({ articleId: "a-001" }),
      makeArticle({ articleId: "a-002" }),
    ]);

    expect(repo.findArticleById("a-001")).not.toBeNull();
    expect(repo.findArticleById("a-002")).not.toBeNull();
  });

  it("returns null for missing article", () => {
    expect(repo.findArticleById("nonexistent")).toBeNull();
  });
});
