import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { env } from '../env.js';
import { makeStableId } from './models.js';
import type { ArchivedPayload, RawPayload, SourceDefinition } from './models.js';

const SAFE_NAME_RE = /[^a-zA-Z0-9._-]+/g;

function safeName(value: string): string {
  const cleaned = value.trim().replace(SAFE_NAME_RE, '-');
  return cleaned.replace(/^-+|-+$/g, '') || 'payload';
}

function extension(payload: RawPayload): string {
  if (payload.extension) return payload.extension;
  if (payload.payloadType.endsWith('xml')) return '.xml';
  if (payload.payloadType.endsWith('html')) return '.html';
  if (payload.payloadType.endsWith('text')) return '.txt';
  if (payload.payloadType.endsWith('json')) return '.json';
  if (payload.payloadType.endsWith('tsv')) return '.tsv';
  return '.bin';
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

export function archivePayload(source: SourceDefinition, payload: RawPayload): ArchivedPayload {
  const fetched = payload.fetchedAt;
  const dayDir = resolve(
    env.HOLLYWOOD_DATA_DIR,
    'raw',
    source.sourceId,
    String(fetched.getUTCFullYear()),
    pad(fetched.getUTCMonth() + 1),
    pad(fetched.getUTCDate()),
  );
  mkdirSync(dayDir, { recursive: true });

  const contentHash = createHash('sha256').update(payload.body).digest('hex');
  const timePart = `${pad(fetched.getUTCHours())}${pad(fetched.getUTCMinutes())}${pad(fetched.getUTCSeconds())}`;
  const filename = `${timePart}_${safeName(payload.logicalId).slice(0, 80)}${extension(payload)}`;
  const path = resolve(dayDir, filename);
  if (!existsSync(path)) {
    writeFileSync(path, payload.body);
  }

  const rawRecordId = makeStableId(
    source.sourceId,
    payload.payloadType,
    payload.logicalId,
    contentHash,
  );
  return {
    rawRecordId,
    sourceId: source.sourceId,
    sourceKind: source.kind,
    payloadType: payload.payloadType,
    logicalId: payload.logicalId,
    contentPath: path,
    contentHash,
    contentType: payload.contentType,
    sourceUrl: payload.sourceUrl,
    canonicalUrl: payload.canonicalUrl,
    fetchedAt: payload.fetchedAt,
    metadataJson: JSON.stringify(payload.metadata),
  };
}
