import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { setupTestDb } from "../db/test-utils.js";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { extractCandidatePhrases, findGroundedEntities, formatGroundedContext } from "./grounding.js";

describe("extractCandidatePhrases", () => {
  it("pulls capitalized name-shaped phrases out of a query", () => {
    expect(extractCandidatePhrases("What's our budget for the Artist One tour with Warner Records?")).toEqual([
      "Artist One",
      "Warner Records",
    ]);
  });

  it("skips leading question words", () => {
    expect(extractCandidatePhrases("What is the release date for Test Album?")).toEqual(["Test Album"]);
  });

  it("returns an empty array when nothing is capitalized", () => {
    expect(extractCandidatePhrases("what is our budget this month")).toEqual([]);
  });
});

describe("findGroundedEntities", () => {
  let entityRepo: EntityRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;

    entityRepo.upsert({
      sourceId: "spotify",
      entityType: "artist",
      name: "Artist One",
      canonicalName: "artist one",
      licenseClass: "api_terms",
    });
    entityRepo.upsert({
      sourceId: "spotify",
      entityType: "title",
      titleType: "album",
      name: "Test Album",
      canonicalName: "test album",
      licenseClass: "api_terms",
    });
  });

  afterEach(() => cleanup());

  it("finds entities from the graph matching capitalized phrases in the query", () => {
    const found = findGroundedEntities("What's the tour budget for Artist One this spring?", entityRepo);
    expect(found).toHaveLength(1);
    expect(found[0]).toMatchObject({ name: "Artist One", entityType: "artist" });
  });

  it("returns an empty array when no phrase matches the graph", () => {
    const found = findGroundedEntities("What's the budget for Nobody Famous?", entityRepo);
    expect(found).toEqual([]);
  });

  it("formats matched entities into a context block", () => {
    const found = findGroundedEntities("Artist One", entityRepo);
    const context = formatGroundedContext(found);
    expect(context).toContain("Artist One");
    expect(formatGroundedContext([])).toBeNull();
  });
});
