import { readFileSync } from "node:fs";
import { createGunzip } from "node:zlib";
import { createInterface } from "node:readline";
import { Readable } from "node:stream";
import { parse } from "csv-parse/sync";
import { env } from "../../env.js";
import { emptyBundle, makeStableId } from "../models.js";
import type {
  CreditRow,
  EntityAliasRow,
  EntityRow,
  IngestOptions,
  NormalizedBundle,
  RawPayload,
  SourceDefinition,
} from "../models.js";
import type { Adapter } from "./base.js";
import type { DbRow } from "../../db/index.js";

const NULL_VALUE = "\\N";

async function downloadTsvLines(url: string, rowLimit?: number): Promise<string[]> {
  const resp = await fetch(url, {
    headers: { "User-Agent": env.HOLLYWOOD_USER_AGENT },
    signal: AbortSignal.timeout(Math.max(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000, 60_000)),
  });
  if (!resp.ok || !resp.body) throw new Error(`Failed to fetch IMDb dataset ${url}: ${resp.status}`);

  const gunzip = createGunzip();
  Readable.fromWeb(resp.body as import("stream/web").ReadableStream).pipe(gunzip);
  const rl = createInterface({ input: gunzip, crlfDelay: Infinity });

  const rows: string[] = [];
  let index = 0;
  for await (const line of rl) {
    rows.push(line);
    if (rowLimit !== undefined && index >= rowLimit) break;
    index++;
  }
  rl.close();
  gunzip.destroy();
  return rows;
}

function parseTsv(text: string): Record<string, string>[] {
  return parse(text, {
    delimiter: "\t",
    columns: true,
    relax_column_count: true,
    skip_empty_lines: true,
    quote: null,
  }) as Record<string, string>[];
}

export class ImdbAdapter implements Adapter {
  constructor(public source: SourceDefinition) {}

  async fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]> {
    const payloads: RawPayload[] = [];
    for (const url of this.source.defaultUrls) {
      const datasetName = url.split("/").pop()!.replace(".tsv.gz", "");
      const rows = await downloadTsvLines(url, options.limit);
      const body = Buffer.from(rows.join("\n") + "\n", "utf-8");
      payloads.push({
        payloadType: "dataset_tsv",
        logicalId: datasetName,
        body,
        contentType: "text/tab-separated-values",
        sourceUrl: url,
        fetchedAt: new Date(),
        metadata: { dataset_name: datasetName },
        extension: ".tsv",
      });
    }
    return payloads;
  }

  async normalizeRawRecords(_runId: string, rawRecords: DbRow[]): Promise<NormalizedBundle> {
    const bundle = emptyBundle();
    const seenEntities = new Set<string>();

    // Group records by dataset so we can enforce processing order.
    // name.basics and title.basics must run before title.principals so that
    // entities are created with real names before principals creates credits
    // that reference them — otherwise principals creates stub entities
    // (nm0005690) and the real names never arrive.
    const byDataset = new Map<string, string>();
    for (const record of rawRecords) {
      if (String(record["payload_type"]) !== "dataset_tsv") continue;
      const metadata = JSON.parse(String(record["metadata_json"] ?? "{}"));
      const datasetName = metadata.dataset_name as string;
      if (!datasetName) continue;
      byDataset.set(datasetName, String(record["content_path"]));
    }

    const order = ["name.basics", "title.basics", "title.principals"];
    for (const datasetName of order) {
      const path = byDataset.get(datasetName);
      if (!path) continue;
      const text = readFileSync(path, "utf-8");
      const rows = parseTsv(text);

      if (datasetName === "name.basics") {
        this.normalizeNameBasics(bundle, rows, seenEntities);
      } else if (datasetName === "title.basics") {
        this.normalizeTitleBasics(bundle, rows, seenEntities);
      } else if (datasetName === "title.principals") {
        this.normalizeTitlePrincipals(bundle, rows, seenEntities);
      }
    }
    return bundle;
  }

  private normalizeNameBasics(bundle: NormalizedBundle, rows: Record<string, string>[], seenEntities: Set<string>): void {
    for (const row of rows) {
      const name = row["primaryName"];
      const nconst = row["nconst"];
      if (!name || !nconst || nconst === NULL_VALUE) continue;
      const entityId = makeStableId("imdb", nconst);
      if (!seenEntities.has(entityId)) {
        seenEntities.add(entityId);
        const entityRow: EntityRow = {
          entityId,
          sourceId: this.source.sourceId,
          externalId: nconst,
          entityType: "person",
          name,
          canonicalName: name.toLowerCase(),
          licenseClass: this.source.licenseClass,
          metadataJson: JSON.stringify({
            birthYear: row["birthYear"] ?? null,
            deathYear: row["deathYear"] ?? null,
            primaryProfession: row["primaryProfession"] ?? null,
            knownForTitles: row["knownForTitles"] ?? null,
          }),
        };
        bundle.entities.push(entityRow);
      }
      const aliasRow: EntityAliasRow = {
        entityAliasId: makeStableId(entityId, name),
        entityId,
        sourceId: this.source.sourceId,
        alias: name,
      };
      bundle.entityAliases.push(aliasRow);
    }
  }

  private normalizeTitleBasics(bundle: NormalizedBundle, rows: Record<string, string>[], seenEntities: Set<string>): void {
    for (const row of rows) {
      const title = row["primaryTitle"];
      const tconst = row["tconst"];
      if (!title || !tconst || tconst === NULL_VALUE) continue;
      const entityId = makeStableId("imdb", tconst);
      if (!seenEntities.has(entityId)) {
        seenEntities.add(entityId);
        const entityRow: EntityRow = {
          entityId,
          sourceId: this.source.sourceId,
          externalId: tconst,
          entityType: "title",
          name: title,
          canonicalName: title.toLowerCase(),
          licenseClass: this.source.licenseClass,
          metadataJson: JSON.stringify({
            titleType: row["titleType"] ?? null,
            originalTitle: row["originalTitle"] ?? null,
            startYear: row["startYear"] ?? null,
            genres: row["genres"] ?? null,
          }),
        };
        bundle.entities.push(entityRow);
      }
    }
  }

  private normalizeTitlePrincipals(bundle: NormalizedBundle, rows: Record<string, string>[], seenEntities: Set<string>): void {
    for (const row of rows) {
      const tconst = row["tconst"];
      const nconst = row["nconst"];
      const role = row["category"];
      const ordering = row["ordering"];
      if (!tconst || !nconst || !role || tconst === NULL_VALUE || nconst === NULL_VALUE) continue;

      const personEid = makeStableId("imdb", nconst);
      const titleEid = makeStableId("imdb", tconst);
      for (const [eid, ename, etype] of [
        [personEid, nconst, "person"],
        [titleEid, tconst, "title"],
      ] as const) {
        if (!seenEntities.has(eid)) {
          seenEntities.add(eid);
          const entityRow: EntityRow = {
            entityId: eid,
            sourceId: this.source.sourceId,
            externalId: ename,
            entityType: etype,
            name: ename,
            canonicalName: ename.toLowerCase(),
            licenseClass: this.source.licenseClass,
            metadataJson: JSON.stringify({ stub: true }),
          };
          bundle.entities.push(entityRow);
        }
      }

      const row2: CreditRow = {
        creditId: makeStableId("imdb", tconst, nconst, role, String(ordering ?? "")),
        sourceId: this.source.sourceId,
        personEntityId: personEid,
        titleEntityId: titleEid,
        role,
        billing: ordering ? Number(ordering) : undefined,
        metadataJson: JSON.stringify({ job: row["job"] ?? null, characters: row["characters"] ?? null }),
      };
      bundle.credits.push(row2);
    }
  }

  doctorChecks() {
    return [{ name: "imdb:config", ok: true, detail: "Configured fetch strategy: streamed_dataset" }];
  }
}
