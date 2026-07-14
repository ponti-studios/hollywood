import type { RawRecordRow } from '../db/repositories/RawRecordRepository.js';
import { IngestService } from '../db/services/IngestService.js';
import type { Adapter } from './adapters/base.js';
import { archivePayload } from './archive.js';
import { bundleCounts } from './models.js';
import type { DoctorCheck, IngestOptions, RunSummary } from './models.js';
import { getSource, listSources } from './registry.js';

const ADAPTERS = new Map<string, Adapter>();

const ingestService = new IngestService();

export function registerAdapter(sourceId: string, adapter: Adapter): void {
  ADAPTERS.set(sourceId, adapter);
}

function getAdapter(sourceId: string): Adapter {
  const adapter = ADAPTERS.get(sourceId);
  if (!adapter) {
    throw new Error(
      `No TypeScript adapter registered yet for source '${sourceId}' (ports land in a later phase)`,
    );
  }
  return adapter;
}

export async function normalizeFlow(sourceId?: string): Promise<Record<string, number>> {
  const rawRecords = ingestService.loadRawRecords(sourceId ? { sourceId } : {});
  const grouped = new Map<string, RawRecordRow[]>();
  for (const record of rawRecords) {
    const key = record.sourceId;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(record);
  }

  const combinedCounts: Record<string, number> = {};
  for (const [groupedSourceId, records] of grouped) {
    getSource(groupedSourceId);
    const adapter = getAdapter(groupedSourceId);
    const runId = ingestService.startRunRaw('normalize', { source_id: groupedSourceId });
    const bundle = await adapter.normalizeRawRecords(runId, records);
    ingestService.applyBundle(bundle);
    const counts = bundleCounts(bundle);
    ingestService.finishRun(runId, 'succeeded', counts);
    for (const [key, value] of Object.entries(counts)) {
      combinedCounts[key] = (combinedCounts[key] ?? 0) + value;
    }
  }
  return combinedCounts;
}

export function sourceDoctorChecks(): DoctorCheck[] {
  const checks: DoctorCheck[] = [];
  for (const source of listSources()) {
    const adapter = ADAPTERS.get(source.sourceId);
    if (adapter?.doctorChecks) {
      checks.push(...adapter.doctorChecks());
    } else if (adapter) {
      checks.push({
        name: `${source.sourceId}:config`,
        ok: true,
        detail: `Configured fetch strategy: ${source.fetchStrategy}`,
      });
    } else {
      checks.push({
        name: `${source.sourceId}:config`,
        ok: true,
        detail: `Configured fetch strategy: ${source.fetchStrategy} (adapter not yet ported)`,
      });
    }
  }
  return checks;
}

export async function runIngestSource(
  sourceId: string,
  options: IngestOptions,
): Promise<RunSummary> {
  const source = getSource(sourceId);
  const adapter = getAdapter(sourceId);
  const runId = ingestService.startRun(source.sourceId, JSON.stringify(options));
  try {
    const payloads = await adapter.fetchRawPayloads(options);
    const archivedPayloads = payloads.map((p) => archivePayload(source, p));
    ingestService.insertRawRecords(runId, archivedPayloads);
    const rawRecords = ingestService.loadRawRecords({ runId });
    const bundle = await adapter.normalizeRawRecords(runId, rawRecords);
    ingestService.applyBundle(bundle);
    const summary: RunSummary = {
      runId,
      sourceId: source.sourceId,
      status: 'succeeded',
      rawRecords: archivedPayloads.length,
      normalized: bundleCounts(bundle),
    };
    ingestService.finishRun(runId, 'succeeded', summary);
    return summary;
  } catch (exc) {
    const error = exc instanceof Error ? exc.message : String(exc);
    ingestService.finishRun(runId, 'failed', { source_id: source.sourceId, error }, error);
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
