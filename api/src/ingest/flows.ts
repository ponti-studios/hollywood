import { archivePayload } from "./archive.js";
import { bundleCounts } from "./models.js";
import type { DoctorCheck, IngestOptions, RunSummary } from "./models.js";
import { getSource, listSources } from "./registry.js";
import {
  applyBundle,
  exportAll,
  exportTable,
  finishRun,
  insertRawRecords,
  loadRawRecords,
  startRun,
  startRunRaw,
} from "./storage.js";
import type { Adapter } from "./adapters/base.js";
import type { DbRow } from "../db/index.js";

/**
 * Adapters are registered here as they're ported (RSS/TMDB/Wikidata in Phase 2,
 * WGA/IMDb in Phase 3). Until a source's adapter is registered, normalizing or
 * re-ingesting that source throws a clear "not yet ported" error.
 */
const ADAPTERS = new Map<string, Adapter>();

export function registerAdapter(sourceId: string, adapter: Adapter): void {
  ADAPTERS.set(sourceId, adapter);
}

function getAdapter(sourceId: string): Adapter {
  const adapter = ADAPTERS.get(sourceId);
  if (!adapter) {
    throw new Error(`No TypeScript adapter registered yet for source '${sourceId}' (ports land in a later phase)`);
  }
  return adapter;
}

export async function normalizeFlow(sourceId?: string): Promise<Record<string, number>> {
  const rawRecords = loadRawRecords(sourceId ? { sourceId } : {});
  const grouped = new Map<string, DbRow[]>();
  for (const record of rawRecords) {
    const key = String(record["source_id"]);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(record);
  }

  const combinedCounts: Record<string, number> = {};
  for (const [groupedSourceId, records] of grouped) {
    getSource(groupedSourceId); // validates the source exists
    const adapter = getAdapter(groupedSourceId);
    const runId = startRunRaw("normalize", { source_id: groupedSourceId });
    const bundle = await adapter.normalizeRawRecords(runId, records);
    applyBundle(bundle);
    const counts = bundleCounts(bundle);
    finishRun(runId, "succeeded", counts);
    for (const [key, value] of Object.entries(counts)) {
      combinedCounts[key] = (combinedCounts[key] ?? 0) + value;
    }
  }
  return combinedCounts;
}

export function exportFlow(fileFormat: "jsonl" | "parquet", outputDir: string, table?: string): string[] {
  if (table) return [exportTable(table, outputDir, fileFormat)];
  return exportAll(outputDir, fileFormat);
}

export function sourceDoctorChecks(): DoctorCheck[] {
  const checks: DoctorCheck[] = [];
  for (const source of listSources()) {
    const adapter = ADAPTERS.get(source.sourceId);
    if (adapter?.doctorChecks) {
      checks.push(...adapter.doctorChecks());
    } else if (adapter) {
      checks.push({ name: `${source.sourceId}:config`, ok: true, detail: `Configured fetch strategy: ${source.fetchStrategy}` });
    } else {
      checks.push({ name: `${source.sourceId}:config`, ok: true, detail: `Configured fetch strategy: ${source.fetchStrategy} (adapter not yet ported)` });
    }
  }
  return checks;
}

// ── Direct (non-orchestrated) ingest, mirrors Python's direct_flows.py ──────

export async function runIngestSource(
  sourceId: string,
  options: IngestOptions,
): Promise<RunSummary> {
  const source = getSource(sourceId);
  const adapter = getAdapter(sourceId);
  const runId = startRun(source.sourceId, JSON.stringify(options));
  try {
    const payloads = await adapter.fetchRawPayloads(options);
    const archivedPayloads = payloads.map((p) => archivePayload(source, p));
    insertRawRecords(runId, archivedPayloads);
    const rawRecords = loadRawRecords({ runId });
    const bundle = await adapter.normalizeRawRecords(runId, rawRecords);
    applyBundle(bundle);
    const summary: RunSummary = {
      runId,
      sourceId: source.sourceId,
      status: "succeeded",
      rawRecords: archivedPayloads.length,
      normalized: bundleCounts(bundle),
    };
    finishRun(runId, "succeeded", summary as unknown as Record<string, unknown>);
    return summary;
  } catch (exc) {
    const error = exc instanceof Error ? exc.message : String(exc);
    finishRun(runId, "failed", { source_id: source.sourceId, error }, error);
    throw exc;
  }
}

export async function runIngestGroup(
  groupName: string,
  options: IngestOptions,
): Promise<RunSummary[]> {
  const summaries: RunSummary[] = [];
  for (const source of listSources(groupName)) {
    summaries.push(await runIngestSource(source.sourceId, options));
  }
  return summaries;
}
