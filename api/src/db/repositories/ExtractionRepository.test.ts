import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { setupTestDb } from "../test-utils.js";
import { ExtractionRepository } from "./ExtractionRepository.js";
import { RawRecordRepository } from "./RawRecordRepository.js";
import { RunRepository } from "./RunRepository.js";

describe("ExtractionRepository", () => {
  let repo: ExtractionRepository;
  let rawRecordRepo: RawRecordRepository;
  let runRepo: RunRepository;
  let cleanup: () => void;
  let docId: string;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new ExtractionRepository(test.db);
    rawRecordRepo = new RawRecordRepository(test.db);
    runRepo = new RunRepository(test.db);
    cleanup = test.cleanup;

    const runId = runRepo.start("test-source", "{}");
    docId = `doc-${Math.random().toString(36).slice(2, 8)}`;
    rawRecordRepo.insertOne({
      id: docId,
      runId,
      sourceId: "test",
      sourceKind: "upload",
      payloadType: "text/plain",
      contentPath: "/data/test.txt",
      contentHash: "abc",
      fetchedAt: new Date().toISOString(),
      metadataJson: "{}",
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("saves and finds an extraction result", () => {
    const id = repo.save({
      documentId: docId,
      schemaVersion: "v1",
      promptVersion: "v1",
      modelName: "gpt-4o",
      status: "succeeded",
      rawJson: '{"raw": "data"}',
      resultJson: '{"name": "Jane"}',
    });

    const found = repo.findById(id);
    expect(found).not.toBeNull();
    expect(found!.modelName).toBe("gpt-4o");
    expect(found!.status).toBe("succeeded");
    expect(found!.resultJson).toBe('{"name": "Jane"}');
  });

  it("finds by document ID", () => {
    repo.save({
      documentId: docId,
      schemaVersion: "v1", promptVersion: "v1",
      modelName: "gpt-4o", status: "succeeded",
      rawJson: "", resultJson: '{"name": "Jane"}',
    });
    repo.save({
      documentId: docId,
      schemaVersion: "v1", promptVersion: "v2",
      modelName: "gpt-4o", status: "succeeded",
      rawJson: "", resultJson: '{"name": "John"}',
    });

    const results = repo.findByDocumentId(docId);
    expect(results).toHaveLength(2);
  });

  it("save is idempotent with explicit ID", () => {
    const id = repo.save({
      id: "extract-001",
      documentId: docId,
      schemaVersion: "v1", promptVersion: "v1",
      modelName: "gpt-4o", status: "succeeded",
      rawJson: "", resultJson: '{"name": "Jane"}',
    });
    const id2 = repo.save({
      id: "extract-001",
      documentId: docId,
      schemaVersion: "v1", promptVersion: "v1",
      modelName: "gpt-4o", status: "succeeded",
      rawJson: "", resultJson: '{"name": "Updated"}',
    });
    expect(id).toBe(id2);
    const found = repo.findById("extract-001");
    expect(found!.resultJson).toBe('{"name": "Updated"}');
  });

  it("returns null for missing extraction", () => {
    expect(repo.findById("nonexistent")).toBeNull();
  });
});
