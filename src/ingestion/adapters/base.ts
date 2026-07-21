import type { RawRecordRow } from '../../domain/repositories/RawRecordRepository.js';
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
