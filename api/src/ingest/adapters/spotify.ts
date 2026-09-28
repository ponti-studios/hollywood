import { readFileSync } from "node:fs";
import { env, SPOTIFY_API_BASE, SPOTIFY_TOKEN_URL } from "../../env.js";
import { emptyBundle, makeStableId } from "../models.js";
import type {
  CreditRow,
  EntityRow,
  IngestOptions,
  NormalizedBundle,
  RawPayload,
  SourceDefinition,
} from "../models.js";
import type { Adapter } from "./base.js";
import type { DbRow } from "../../db/index.js";

/**
 * Ingests Spotify's new-release albums as the seed for the music side of the
 * entity graph: each album becomes a `title` (titleType "album"), each credited
 * artist becomes an `artist` entity, linked via a `primary_artist` credit.
 */
export class SpotifyAdapter implements Adapter {
  constructor(public source: SourceDefinition) {}

  private tokenCache: { token: string; expiresAt: number } | null = null;

  private async getAccessToken(): Promise<string> {
    if (!env.SPOTIFY_CLIENT_ID || !env.SPOTIFY_CLIENT_SECRET) {
      throw new Error("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required for the spotify source.");
    }
    if (this.tokenCache && this.tokenCache.expiresAt > Date.now()) return this.tokenCache.token;

    const basic = Buffer.from(`${env.SPOTIFY_CLIENT_ID}:${env.SPOTIFY_CLIENT_SECRET}`).toString("base64");
    const resp = await fetch(SPOTIFY_TOKEN_URL, {
      method: "POST",
      headers: {
        Authorization: `Basic ${basic}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "grant_type=client_credentials",
      signal: AbortSignal.timeout(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000),
    });
    if (!resp.ok) throw new Error(`Spotify token request failed: ${resp.status}`);
    const json = (await resp.json()) as { access_token: string; expires_in: number };
    this.tokenCache = { token: json.access_token, expiresAt: Date.now() + (json.expires_in - 60) * 1000 };
    return this.tokenCache.token;
  }

  private async get(token: string, path: string, params: Record<string, string> = {}): Promise<Record<string, unknown>> {
    const url = new URL(`${SPOTIFY_API_BASE}${path}`);
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
    const resp = await fetch(url, {
      headers: { Authorization: `Bearer ${token}`, "User-Agent": env.HOLLYWOOD_USER_AGENT },
      signal: AbortSignal.timeout(env.HOLLYWOOD_REQUEST_TIMEOUT_SECONDS * 1000),
    });
    if (!resp.ok) throw new Error(`Spotify request failed: ${path} -> ${resp.status}`);
    return (await resp.json()) as Record<string, unknown>;
  }

  async fetchRawPayloads(options: IngestOptions): Promise<RawPayload[]> {
    const payloads: RawPayload[] = [];
    const limit = options.limit ?? 5;
    const token = await this.getAccessToken();

    const newReleases = await this.get(token, "/browse/new-releases", { limit: String(Math.min(limit, 50)) });
    payloads.push({
      payloadType: "api_json",
      logicalId: "new_releases",
      body: Buffer.from(JSON.stringify(newReleases), "utf-8"),
      contentType: "application/json",
      sourceUrl: `${SPOTIFY_API_BASE}/browse/new-releases`,
      fetchedAt: new Date(),
      metadata: { endpoint: "/browse/new-releases", kind: "new_releases_list" },
      extension: ".json",
    });

    const albums = ((newReleases["albums"] as Record<string, unknown>)?.["items"] as Record<string, unknown>[]) ?? [];
    for (const album of albums.slice(0, limit)) {
      const albumId = album["id"];
      if (albumId === undefined || albumId === null) continue;
      const endpoint = `/albums/${albumId}`;
      const detail = await this.get(token, endpoint);
      payloads.push({
        payloadType: "api_json",
        logicalId: `album-${albumId}`,
        body: Buffer.from(JSON.stringify(detail), "utf-8"),
        contentType: "application/json",
        sourceUrl: `${SPOTIFY_API_BASE}${endpoint}`,
        fetchedAt: new Date(),
        metadata: { endpoint, kind: "album" },
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
      if (metadata.kind !== "album") continue;

      const document = JSON.parse(readFileSync(String(record["content_path"]), "utf-8")) as Record<string, unknown>;
      this.normalizeAlbum(bundle, document, seenEntities);
    }

    return bundle;
  }

  private normalizeAlbum(bundle: NormalizedBundle, document: Record<string, unknown>, seenEntities: Set<string>): void {
    const albumId = String(document["id"]);
    const albumName = String(document["name"] ?? albumId);
    const albumEntityId = makeStableId("spotify", "album", albumId);
    if (!seenEntities.has(albumEntityId)) {
      seenEntities.add(albumEntityId);
      const row: EntityRow = {
        entityId: albumEntityId,
        sourceId: this.source.sourceId,
        externalId: albumId,
        entityType: "title",
        name: albumName,
        canonicalName: albumName.toLowerCase(),
        licenseClass: this.source.licenseClass,
        metadataJson: JSON.stringify({
          title_type: "album",
          album_type: document["album_type"] ?? null,
          release_date: document["release_date"] ?? null,
          total_tracks: document["total_tracks"] ?? null,
          spotify_url: (document["external_urls"] as Record<string, unknown> | undefined)?.["spotify"] ?? null,
        }),
      };
      bundle.entities.push(row);
    }

    const artists = (document["artists"] as Record<string, unknown>[] | undefined) ?? [];
    for (const artist of artists) {
      const artistName = artist["name"] as string | undefined;
      const artistId = artist["id"];
      if (!artistName || artistId === undefined || artistId === null) continue;

      const artistEntityId = makeStableId("spotify", "artist", String(artistId));
      if (!seenEntities.has(artistEntityId)) {
        seenEntities.add(artistEntityId);
        bundle.entities.push({
          entityId: artistEntityId,
          sourceId: this.source.sourceId,
          externalId: String(artistId),
          entityType: "artist",
          name: artistName,
          canonicalName: artistName.toLowerCase(),
          licenseClass: this.source.licenseClass,
          metadataJson: JSON.stringify({
            spotify_url: (artist["external_urls"] as Record<string, unknown> | undefined)?.["spotify"] ?? null,
          }),
        });
      }

      const credit: CreditRow = {
        creditId: makeStableId("spotify", albumId, String(artistId)),
        sourceId: this.source.sourceId,
        personEntityId: artistEntityId,
        titleEntityId: albumEntityId,
        role: "primary_artist",
        metadataJson: "{}",
      };
      bundle.credits.push(credit);
    }
  }

  doctorChecks(): { name: string; ok: boolean; detail: string }[] {
    const ok = Boolean(env.SPOTIFY_CLIENT_ID && env.SPOTIFY_CLIENT_SECRET);
    return [
      {
        name: "spotify:config",
        ok,
        detail: ok ? "SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET configured" : "SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET missing",
      },
    ];
  }
}
