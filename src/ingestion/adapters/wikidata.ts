import { readFileSync } from 'node:fs';

import type { RawRecordRow } from '../../domain/repositories/RawRecordRepository.js';
import { env } from '../../env.js';
import { emptyBundle, makeStableId } from '../models.js';
import type {
  EntityAliasRow,
  EntityRow,
  IngestOptions,
  NormalizedBundle,
  RawPayload,
  SourceDefinition,
} from '../models.js';
import type { Adapter } from './base.js';

const WIKIDATA_QUERY = `
SELECT ?item ?itemLabel ?occupationLabel WHERE {
  VALUES ?occupation { wd:Q33999 wd:Q2526255 wd:Q28389 }
  ?item wdt:P31 wd:Q5;
        wdt:P106 ?occupation.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT {limit}
`;

interface SparqlBinding {
  item?: { value?: string };
  itemLabel?: { value?: string };
  occupationLabel?: { value?: string };
}

export class WikidataAdapter implements Adapter {
  constructor(public source: SourceDefinition) {}

  async fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]> {
    const limit = options.limit ?? 25;
    const query = WIKIDATA_QUERY.replace('{limit}', String(limit));
    const url = new URL(this.source.defaultUrls[0]!);
    url.searchParams.set('query', query);
    url.searchParams.set('format', 'json');

    const resp = await fetch(url, {
      headers: {
        Accept: 'application/sparql-results+json',
        'User-Agent': env.HOLLYWOOD_USER_AGENT,
      },
      signal: AbortSignal.timeout(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000),
    });
    if (!resp.ok) throw new Error(`Wikidata request failed: ${resp.status}`);
    const body = Buffer.from(await resp.arrayBuffer());

    return [
      {
        payloadType: 'api_json',
        logicalId: `wikidata-${limit}`,
        body,
        contentType: resp.headers.get('content-type') ?? 'application/json',
        sourceUrl: resp.url,
        fetchedAt: new Date(),
        metadata: { query, limit },
        extension: '.json',
      },
    ];
  }

  async normalizeRawRecords(_runId: string, rawRecords: RawRecordRow[]): Promise<NormalizedBundle> {
    const bundle = emptyBundle();
    for (const record of rawRecords) {
      if (record.payloadType !== 'api_json') continue;
      const document = JSON.parse(readFileSync(record.contentPath, 'utf-8')) as {
        results?: { bindings?: SparqlBinding[] };
      };
      const bindings = document.results?.bindings ?? [];

      for (const item of bindings) {
        const itemUrl = item.item?.value;
        const label = item.itemLabel?.value;
        const occupation = item.occupationLabel?.value ?? null;
        if (!itemUrl || !label) continue;

        const qid = itemUrl.split('/').pop()!;
        const entityId = makeStableId('wikidata', qid);
        const entityRow: EntityRow = {
          entityId,
          sourceId: this.source.sourceId,
          externalId: qid,
          entityType: 'person',
          name: label,
          canonicalName: label.toLowerCase(),
          metadataJson: JSON.stringify({ occupation }),
        };
        bundle.entities.push(entityRow);

        const aliasRow: EntityAliasRow = {
          entityAliasId: makeStableId(entityId, label),
          entityId,
          sourceId: this.source.sourceId,
          alias: label,
        };
        bundle.entityAliases.push(aliasRow);
      }
    }
    return bundle;
  }
}
