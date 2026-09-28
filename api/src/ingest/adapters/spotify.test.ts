import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { getSource } from "../registry.js";
import { SpotifyAdapter } from "./spotify.js";
import type { DbRow } from "../../db/index.js";

function writeAlbumRecord(album: Record<string, unknown>): DbRow {
  const dir = mkdtempSync(join(tmpdir(), "hollywood-spotify-test-"));
  const contentPath = join(dir, "album.json");
  writeFileSync(contentPath, JSON.stringify(album));
  return {
    payload_type: "api_json",
    content_path: contentPath,
    metadata_json: JSON.stringify({ endpoint: `/albums/${album["id"]}`, kind: "album" }),
  } as unknown as DbRow;
}

describe("SpotifyAdapter", () => {
  const adapter = new SpotifyAdapter(getSource("spotify"));

  it("normalizes an album into a title entity and artist credits", async () => {
    const record = writeAlbumRecord({
      id: "album1",
      name: "Test Album",
      album_type: "album",
      release_date: "2026-01-01",
      total_tracks: 10,
      external_urls: { spotify: "https://open.spotify.com/album/album1" },
      artists: [
        { id: "artist1", name: "Artist One", external_urls: { spotify: "https://open.spotify.com/artist/artist1" } },
        { id: "artist2", name: "Artist Two", external_urls: { spotify: "https://open.spotify.com/artist/artist2" } },
      ],
    });

    const bundle = await adapter.normalizeRawRecords("run1", [record]);

    expect(bundle.entities).toHaveLength(3);
    const album = bundle.entities.find((e) => e.entityType === "title");
    expect(album?.name).toBe("Test Album");
    expect(JSON.parse(album!.metadataJson).title_type).toBe("album");

    const artists = bundle.entities.filter((e) => e.entityType === "artist");
    expect(artists.map((a) => a.name).sort()).toEqual(["Artist One", "Artist Two"]);

    expect(bundle.credits).toHaveLength(2);
    for (const credit of bundle.credits) {
      expect(credit.role).toBe("primary_artist");
      expect(credit.titleEntityId).toBe(album!.entityId);
    }
  });

  it("skips raw records that are not album payloads", async () => {
    const record = {
      payload_type: "api_json",
      content_path: "/dev/null",
      metadata_json: JSON.stringify({ endpoint: "/browse/new-releases", kind: "new_releases_list" }),
    } as unknown as DbRow;

    const bundle = await adapter.normalizeRawRecords("run1", [record]);

    expect(bundle.entities).toHaveLength(0);
    expect(bundle.credits).toHaveLength(0);
  });

  it("reports doctor check status from env config", () => {
    const checks = adapter.doctorChecks?.() ?? [];
    expect(checks).toHaveLength(1);
    expect(checks[0]?.name).toBe("spotify:config");
  });
});
