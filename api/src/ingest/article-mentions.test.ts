import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArticleMentions, SCHEMA_VERSION_V1 } from "./article-mentions.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

function validPacket(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: SCHEMA_VERSION_V1,
    people: [
      {
        name: "Jane Doe",
        role_hint: "director",
        related_to: [{ name: "The Crown", type: "title", relationship: "attached to direct" }],
      },
    ],
    titles: [{ name: "The Crown", format_hint: "series" }],
    companies: [{ name: "Netflix", type_hint: "streamer" }],
    ...overrides,
  };
}

describe("parseArticleMentions", () => {
  it("parses a valid packet", () => {
    const result = parseArticleMentions(validPacket());
    expect(result.schemaVersion).toBe(SCHEMA_VERSION_V1);
    expect(result.people).toHaveLength(1);
    expect(result.people[0]).toEqual({
      name: "Jane Doe",
      roleHint: "director",
      relatedTo: [{ name: "The Crown", type: "title", relationship: "attached to direct" }],
    });
    expect(result.titles).toEqual([{ name: "The Crown", formatHint: "series" }]);
    expect(result.companies).toEqual([{ name: "Netflix", typeHint: "streamer" }]);
  });

  it("defaults omitted arrays to empty", () => {
    const result = parseArticleMentions({ schema_version: SCHEMA_VERSION_V1 });
    expect(result.people).toEqual([]);
    expect(result.titles).toEqual([]);
    expect(result.companies).toEqual([]);
  });

  it("throws when a person is missing a name", () => {
    const packet = validPacket({ people: [{ role_hint: "director" }] });
    expect(() => parseArticleMentions(packet)).toThrow();
  });

  it("throws when related_to has an unrecognized type", () => {
    const packet = validPacket({
      people: [
        {
          name: "Jane Doe",
          related_to: [{ name: "The Crown", type: "network", relationship: "attached to direct" }],
        },
      ],
    });
    expect(() => parseArticleMentions(packet)).toThrow();
  });

  it("throws on an unsupported schema_version", () => {
    const packet = validPacket({ schema_version: "v0_bogus" });
    expect(() => parseArticleMentions(packet)).toThrow(/unsupported schema_version/);
  });

  it("trims whitespace and normalizes empty hint strings to null", () => {
    const packet = validPacket({
      people: [{ name: "  Jane Doe  ", role_hint: "  ", related_to: [] }],
    });
    const result = parseArticleMentions(packet);
    expect(result.people[0]!.name).toBe("Jane Doe");
    expect(result.people[0]!.roleHint).toBeNull();
  });

  // Real LLM response, captured from a live POST /articles/enrich run against
  // an actual Variety article — not hand-written. See task in the article
  // enrichment plan for how it was captured.
  it("parses a real captured LLM response", () => {
    const raw = JSON.parse(
      readFileSync(resolve(__dirname, "__fixtures__/article-mentions/real-llm-response.json"), "utf-8"),
    );
    const result = parseArticleMentions(raw);

    expect(result.people).toHaveLength(5);
    expect(result.titles).toHaveLength(4);
    expect(result.companies).toHaveLength(3);

    const director = result.people.find((p) => p.name === "Natalia Solórzano Vásquez");
    expect(director).toBeDefined();
    expect(director!.relatedTo).toContainEqual({
      name: "Spells to Revive a Witch",
      type: "title",
      relationship: "director",
    });
    // A fictional character the LLM listed with type "person" — the schema
    // accepts it (person-to-person mentions are valid, just not turned into
    // structured credits/company_relations by the enrichment service).
    expect(director!.relatedTo).toContainEqual({
      name: "Soralla de Persia",
      type: "person",
      relationship: "casting call to embody",
    });
  });
});
