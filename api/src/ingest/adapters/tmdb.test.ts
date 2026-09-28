import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { getSource } from "../registry.js";
import { TmdbAdapter } from "./tmdb.js";
import type { DbRow } from "../../db/index.js";

function writeTitleRecord(mediaType: "movie" | "tv", doc: Record<string, unknown>): DbRow {
  const dir = mkdtempSync(join(tmpdir(), "hollywood-tmdb-test-"));
  const contentPath = join(dir, "title.json");
  writeFileSync(contentPath, JSON.stringify(doc));
  return {
    payload_type: "api_json",
    content_path: contentPath,
    metadata_json: JSON.stringify({ endpoint: `/${mediaType}/${doc["id"]}`, media_type: mediaType }),
  } as unknown as DbRow;
}

describe("TmdbAdapter", () => {
  const adapter = new TmdbAdapter(getSource("tmdb"));

  it("maps budget and revenue for a movie", async () => {
    const record = writeTitleRecord("movie", {
      id: 1,
      title: "Test Movie",
      external_ids: {},
      budget: 100_000_000,
      revenue: 250_000_000,
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    const title = bundle.entities.find((e) => e.entityType === "title");
    const meta = JSON.parse(title!.metadataJson);

    expect(meta.budget).toBe(100_000_000);
    expect(meta.revenue).toBe(250_000_000);
    expect(meta.budgetCurrency).toBe("USD");
  });

  it("treats TMDb's 0 as unknown and omits budget/revenue", async () => {
    const record = writeTitleRecord("movie", {
      id: 2,
      title: "Unknown Finance Movie",
      external_ids: {},
      budget: 0,
      revenue: 0,
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    const title = bundle.entities.find((e) => e.entityType === "title");
    const meta = JSON.parse(title!.metadataJson);

    expect(meta.budget).toBeUndefined();
    expect(meta.revenue).toBeUndefined();
    expect(meta.budgetCurrency).toBeUndefined();
    expect("budget" in meta).toBe(false);
  });

  it("omits only the zero side when one of budget/revenue is known", async () => {
    const record = writeTitleRecord("movie", {
      id: 3,
      title: "Partial Finance Movie",
      external_ids: {},
      budget: 0,
      revenue: 500_000,
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    const title = bundle.entities.find((e) => e.entityType === "title");
    const meta = JSON.parse(title!.metadataJson);

    expect(meta.budget).toBeUndefined();
    expect(meta.revenue).toBe(500_000);
    expect(meta.budgetCurrency).toBe("USD");
  });

  it("does not add budget/revenue fields for tv media type", async () => {
    const record = writeTitleRecord("tv", {
      id: 4,
      name: "Test Show",
      external_ids: {},
      // tv documents never carry budget/revenue from TMDb, but assert
      // robustness even if present, since document is Record<string, unknown>.
      budget: 999,
      revenue: 999,
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    const title = bundle.entities.find((e) => e.entityType === "title");
    const meta = JSON.parse(title!.metadataJson);

    expect(meta.budget).toBeUndefined();
    expect(meta.revenue).toBeUndefined();
    expect(meta.budgetCurrency).toBeUndefined();
  });

  it("maps production companies to company entities and title_companies rows for a movie", async () => {
    const record = writeTitleRecord("movie", {
      id: 5,
      title: "Studio Movie",
      external_ids: {},
      production_companies: [
        { id: 420, name: "Marvel Studios", origin_country: "US" },
        { id: 7505, name: "Marvel Entertainment", origin_country: "US" },
      ],
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    const title = bundle.entities.find((e) => e.entityType === "title");
    const companies = bundle.entities.filter((e) => e.entityType === "company");

    expect(companies.map((c) => c.name).sort()).toEqual(["Marvel Entertainment", "Marvel Studios"]);
    for (const company of companies) {
      expect(JSON.parse(company.metadataJson).company_type).toBe("production_company");
    }

    expect(bundle.titleCompanies).toHaveLength(2);
    for (const tc of bundle.titleCompanies) {
      expect(tc.relationship).toBe("production");
      expect(tc.titleEntityId).toBe(title!.entityId);
    }
  });

  it("maps production companies for a tv show too", async () => {
    const record = writeTitleRecord("tv", {
      id: 6,
      name: "Studio Show",
      external_ids: {},
      production_companies: [{ id: 3268, name: "HBO", origin_country: "US" }],
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    const companies = bundle.entities.filter((e) => e.entityType === "company");

    expect(companies.map((c) => c.name)).toEqual(["HBO"]);
    expect(bundle.titleCompanies).toHaveLength(1);
  });

  it("skips raw records that are not api_json trending payloads", async () => {
    const record = {
      payload_type: "api_json",
      content_path: "/dev/null",
      metadata_json: JSON.stringify({ endpoint: "/trending/all/day" }),
    } as unknown as DbRow;

    const bundle = await adapter.normalizeRawRecords("run1", [record]);
    expect(bundle.entities).toHaveLength(0);
  });

  it("reports doctor check status from env config", () => {
    const checks = adapter.doctorChecks?.() ?? [];
    expect(checks).toHaveLength(1);
    expect(checks[0]?.name).toBe("tmdb:config");
  });
});
