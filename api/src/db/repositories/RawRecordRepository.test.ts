import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { setupTestDb } from "../test-utils.js";
import { RawRecordRepository, type RawRecordInsert } from "./RawRecordRepository.js";
import { RunRepository } from "./RunRepository.js";

function makeRecord(
  runId: string,
  overrides: Partial<RawRecordInsert> = {},
): RawRecordInsert {
  return {
    id: `raw-${Math.random().toString(36).slice(2, 8)}`,
    runId,
    sourceId: "variety",
    sourceKind: "rss",
    payloadType: "application/rss+xml",
    contentPath: "/data/variety/feed.xml",
    contentHash: "abc123",
    contentType: "text/xml",
    sourceUrl: "https://variety.com/feed",
    canonicalUrl: null,
    fetchedAt: new Date().toISOString(),
    metadataJson: "{}",
    ...overrides,
  };
}

describe("RawRecordRepository", () => {
  let repo: RawRecordRepository;
  let runRepo: RunRepository;
  let cleanup: () => void;
  let runId: string;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new RawRecordRepository(test.db);
    runRepo = new RunRepository(test.db);
    cleanup = test.cleanup;
    runId = runRepo.start("test-source", "{}");
  });

  afterEach(() => {
    cleanup();
  });

  it("inserts and finds a single record by ID", () => {
    const record = makeRecord(runId, { id: "rec-001" });
    repo.insertOne(record);
    const found = repo.findById("rec-001");
    expect(found).not.toBeNull();
    expect(found!.sourceId).toBe("variety");
    expect(found!.contentHash).toBe("abc123");
  });

  it("inserts a batch and finds by run ID", () => {
    const runB = runRepo.start("other-source", "{}");
    repo.insertBatch([
      makeRecord(runId, { id: "r1" }),
      makeRecord(runId, { id: "r2" }),
      makeRecord(runB, { id: "r3" }),
    ]);

    const runARecords = repo.findByRunId(runId);
    expect(runARecords).toHaveLength(2);
    expect(runARecords.map((r) => r.id).sort()).toEqual(["r1", "r2"]);
  });

  it("finds by source ID", () => {
    const runB = runRepo.start("other-source", "{}");
    repo.insertBatch([
      makeRecord(runId, { id: "r1", sourceId: "variety" }),
      makeRecord(runB, { id: "r2", sourceId: "deadline" }),
      makeRecord(runId, { id: "r3", sourceId: "variety" }),
    ]);

    const varietyRecords = repo.findBySourceId("variety");
    expect(varietyRecords).toHaveLength(2);
  });

  it("finds with combined source and run filter", () => {
    const runB = runRepo.start("other-source", "{}");
    repo.insertBatch([
      makeRecord(runId, { id: "r1", sourceId: "variety" }),
      makeRecord(runId, { id: "r2", sourceId: "deadline" }),
      makeRecord(runB, { id: "r3", sourceId: "variety" }),
    ]);

    const filtered = repo.find({ runId, sourceId: "variety" });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].id).toBe("r1");
  });

  it("returns empty arrays for missing records", () => {
    expect(repo.findById("nonexistent")).toBeNull();
    expect(repo.findByRunId("no-such-run")).toHaveLength(0);
    expect(repo.findBySourceId("no-such-source")).toHaveLength(0);
  });

  it("orders by fetchedAt ascending", () => {
    repo.insertBatch([
      makeRecord(runId, { id: "r1", fetchedAt: "2025-01-03T00:00:00.000Z" }),
      makeRecord(runId, { id: "r2", fetchedAt: "2025-01-01T00:00:00.000Z" }),
      makeRecord(runId, { id: "r3", fetchedAt: "2025-01-02T00:00:00.000Z" }),
    ]);

    const records = repo.findByRunId(runId);
    expect(records).toHaveLength(3);
    expect(records[0].id).toBe("r2");
    expect(records[1].id).toBe("r3");
    expect(records[2].id).toBe("r1");
  });
});
