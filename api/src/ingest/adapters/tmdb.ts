import { readFileSync } from "node:fs";
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

const TMDB_BASE_URL = "https://api.themoviedb.org/3";

export class TmdbAdapter implements Adapter {
  constructor(public source: SourceDefinition) {}

  private async get(path: string, params: Record<string, string> = {}): Promise<Record<string, unknown>> {
    if (!env.TMDB_API_KEY) throw new Error("TMDB_API_KEY is required for the tmdb source.");
    const url = new URL(`${TMDB_BASE_URL}${path}`);
    url.searchParams.set("api_key", env.TMDB_API_KEY);
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
    const resp = await fetch(url, {
      headers: { "User-Agent": env.HOLLYWOOD_USER_AGENT },
      signal: AbortSignal.timeout(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000),
    });
    if (!resp.ok) throw new Error(`TMDB request failed: ${path} -> ${resp.status}`);
    return (await resp.json()) as Record<string, unknown>;
  }

  async fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]> {
    const payloads: RawPayload[] = [];
    const limit = options.limit ?? 5;

    const trending = await this.get("/trending/all/day");
    const items = ((trending["results"] as Record<string, unknown>[]) ?? []).slice(0, limit);
    payloads.push({
      payloadType: "api_json",
      logicalId: "trending_all_day",
      body: Buffer.from(JSON.stringify(trending), "utf-8"),
      contentType: "application/json",
      sourceUrl: `${TMDB_BASE_URL}/trending/all/day`,
      fetchedAt: new Date(),
      metadata: { endpoint: "/trending/all/day" },
      extension: ".json",
    });

    for (const item of items) {
      const mediaType = item["media_type"] as string | undefined;
      const itemId = item["id"];
      if (!mediaType || !["movie", "tv", "person"].includes(mediaType) || itemId === undefined || itemId === null) continue;

      let endpoint: string;
      let detail: Record<string, unknown>;
      if (mediaType === "person") {
        endpoint = `/person/${itemId}`;
        detail = await this.get(endpoint, { append_to_response: "external_ids" });
      } else {
        endpoint = `/${mediaType}/${itemId}`;
        detail = await this.get(endpoint, { append_to_response: "credits,external_ids" });
      }
      detail["media_type"] = mediaType;

      payloads.push({
        payloadType: "api_json",
        logicalId: `${mediaType}-${itemId}`,
        body: Buffer.from(JSON.stringify(detail), "utf-8"),
        contentType: "application/json",
        sourceUrl: `${TMDB_BASE_URL}${endpoint}`,
        fetchedAt: new Date(),
        metadata: { endpoint, media_type: mediaType },
        extension: ".json",
      });
    }

    return payloads;
  }

  async normalizeRawRecords(_runId: string, rawRecords: DbRow[]): Promise<NormalizedBundle> {
    const bundle = emptyBundle();
    const seenEntities = new Set<string>();

    for (const record of rawRecords) {
      if (String(record["payload_type"]) !== "api_json") continue;
      const metadata = JSON.parse(String(record["metadata_json"] ?? "{}"));
      if (metadata.endpoint === "/trending/all/day") continue;

      const document = JSON.parse(readFileSync(String(record["content_path"]), "utf-8")) as Record<string, unknown>;
      const mediaType = metadata.media_type ?? document["media_type"];

      if (mediaType === "person") {
        this.normalizePerson(bundle, document, seenEntities);
      } else if (mediaType === "movie" || mediaType === "tv") {
        this.normalizeTitle(bundle, document, mediaType, seenEntities);
      }
    }

    return bundle;
  }

  private normalizePerson(bundle: NormalizedBundle, document: Record<string, unknown>, seenEntities: Set<string>): void {
    const personId = String(document["id"]);
    const name = String(document["name"] ?? personId);
    const entityId = makeStableId("tmdb", "person", personId);
    if (!seenEntities.has(entityId)) {
      seenEntities.add(entityId);
      const row: EntityRow = {
        entityId,
        sourceId: this.source.sourceId,
        externalId: personId,
        entityType: "person",
        name,
        canonicalName: name.toLowerCase(),
        licenseClass: this.source.licenseClass,
        metadataJson: JSON.stringify({
          known_for_department: document["known_for_department"] ?? null,
          external_ids: document["external_ids"] ?? {},
        }),
      };
      bundle.entities.push(row);
    }
    const aliases = (document["also_known_as"] as string[] | undefined) ?? [];
    for (const alias of aliases.slice(0, 5)) {
      if (!alias) continue;
      const row: EntityAliasRow = {
        entityAliasId: makeStableId(entityId, alias),
        entityId,
        sourceId: this.source.sourceId,
        alias,
      };
      bundle.entityAliases.push(row);
    }
  }

  private normalizeTitle(bundle: NormalizedBundle, document: Record<string, unknown>, mediaType: string, seenEntities: Set<string>): void {
    const titleId = String(document["id"]);
    const titleName = String(document["title"] ?? document["name"] ?? titleId);
    const titleEntityId = makeStableId("tmdb", mediaType, titleId);
    if (!seenEntities.has(titleEntityId)) {
      seenEntities.add(titleEntityId);
      const row: EntityRow = {
        entityId: titleEntityId,
        sourceId: this.source.sourceId,
        externalId: titleId,
        entityType: "title",
        name: titleName,
        canonicalName: titleName.toLowerCase(),
        licenseClass: this.source.licenseClass,
        metadataJson: JSON.stringify({ media_type: mediaType, external_ids: document["external_ids"] ?? {} }),
      };
      bundle.entities.push(row);
    }

    const credits = (document["credits"] as Record<string, unknown>) ?? {};
    const cast = ((credits["cast"] as Record<string, unknown>[]) ?? []).slice(0, 20);
    const crew = ((credits["crew"] as Record<string, unknown>[]) ?? []).slice(0, 20);

    for (const castMember of cast) {
      const personName = castMember["name"] as string | undefined;
      const personId = castMember["id"];
      if (!personName || personId === undefined || personId === null) continue;
      const personEntityId = makeStableId("tmdb", "person", String(personId));
      if (!seenEntities.has(personEntityId)) {
        seenEntities.add(personEntityId);
        bundle.entities.push({
          entityId: personEntityId,
          sourceId: this.source.sourceId,
          externalId: String(personId),
          entityType: "person",
          name: personName,
          canonicalName: personName.toLowerCase(),
          licenseClass: this.source.licenseClass,
          metadataJson: JSON.stringify({ known_for_department: castMember["known_for_department"] ?? null }),
        });
      }
      const row: CreditRow = {
        creditId: makeStableId("tmdb", titleId, String(personId), String(castMember["credit_id"] ?? "")),
        sourceId: this.source.sourceId,
        personEntityId,
        titleEntityId,
        role: String(castMember["character"] ?? "cast"),
        billing: castMember["order"] !== undefined && castMember["order"] !== null ? Number(castMember["order"]) : undefined,
        metadataJson: JSON.stringify({ credit_type: "cast" }),
      };
      bundle.credits.push(row);
    }

    for (const crewMember of crew) {
      const personName = crewMember["name"] as string | undefined;
      const personId = crewMember["id"];
      if (!personName || personId === undefined || personId === null) continue;
      const personEntityId = makeStableId("tmdb", "person", String(personId));
      if (!seenEntities.has(personEntityId)) {
        seenEntities.add(personEntityId);
        bundle.entities.push({
          entityId: personEntityId,
          sourceId: this.source.sourceId,
          externalId: String(personId),
          entityType: "person",
          name: personName,
          canonicalName: personName.toLowerCase(),
          licenseClass: this.source.licenseClass,
          metadataJson: JSON.stringify({ department: crewMember["department"] ?? null }),
        });
      }
      const row: CreditRow = {
        creditId: makeStableId("tmdb", titleId, String(personId), String(crewMember["credit_id"] ?? "")),
        sourceId: this.source.sourceId,
        personEntityId,
        titleEntityId,
        role: String(crewMember["job"] ?? crewMember["department"] ?? "crew"),
        billing: undefined,
        metadataJson: JSON.stringify({ credit_type: "crew" }),
      };
      bundle.credits.push(row);
    }
  }

  doctorChecks(): { name: string; ok: boolean; detail: string }[] {
    return [
      {
        name: "tmdb:config",
        ok: Boolean(env.TMDB_API_KEY),
        detail: env.TMDB_API_KEY ? "TMDB_API_KEY configured" : "TMDB_API_KEY missing",
      },
    ];
  }
}
