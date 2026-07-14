import type { RawRecordRow } from '../../db/repositories/RawRecordRepository.js';
import type {
  DoctorCheck,
  IngestOptions,
  NormalizedBundle,
  RawPayload,
  SourceDefinition,
} from '../models.js';

export interface Adapter {
  source: SourceDefinition;
  fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]>;
  normalizeRawRecords(runId: string, rawRecords: RawRecordRow[]): Promise<NormalizedBundle>;
  doctorChecks?(): DoctorCheck[];
}

export function defaultDoctorChecks(source: SourceDefinition): DoctorCheck[] {
  return [
    {
      name: `${source.sourceId}:config`,
      ok: true,
      detail: `Configured fetch strategy: ${source.fetchStrategy}`,
    },
  ];
}
