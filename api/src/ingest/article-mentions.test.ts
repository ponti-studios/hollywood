import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArticleMentions, SCHEMA_VERSION_V2 } from "./article-mentions.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

function validPacket(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: SCHEMA_VERSION_V2,
    people: [
      {
        name: "Jane Doe",
        role_hint: "director",
        related_to: [{ name: "The Crown", type: "title", relationship: "director" }],
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
    expect(result.schemaVersion).toBe(SCHEMA_VERSION_V2);
    expect(result.people).toHaveLength(1);
    expect(result.people[0]).toEqual({
      name: "Jane Doe",
      roleHint: "director",
      relatedTo: [{ name: "The Crown", type: "title", relationship: "director", character: null }],
    });
    expect(result.titles).toEqual([{ name: "The Crown", formatHint: "series" }]);
    expect(result.companies).toEqual([{ name: "Netflix", typeHint: "streamer" }]);
  });

  it("defaults omitted arrays to empty", () => {
    const result = parseArticleMentions({ schema_version: SCHEMA_VERSION_V2 });
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
          related_to: [{ name: "The Crown", type: "network", relationship: "director" }],
        },
      ],
    });
    expect(() => parseArticleMentions(packet)).toThrow();
  });

  it("throws when a title relationship isn't in the controlled vocabulary", () => {
    const packet = validPacket({
      people: [
        {
          name: "Jane Doe",
          related_to: [{ name: "The Crown", type: "title", relationship: "starred alongside Nicole Kidman" }],
        },
      ],
    });
    expect(() => parseArticleMentions(packet)).toThrow(/must be one of/);
  });

  it("throws on an unsupported schema_version", () => {
    const packet = validPacket({ schema_version: "v0_bogus" });
    expect(() => parseArticleMentions(packet)).toThrow(/unsupported schema_version/);
  });

  it("keeps character when relationship is actor", () => {
    const packet = validPacket({
      people: [
        {
          name: "Jane Doe",
          related_to: [{ name: "The Crown", type: "title", relationship: "actor", character: "Queen Elizabeth" }],
        },
      ],
    });
    const result = parseArticleMentions(packet);
    expect(result.people[0]!.relatedTo[0]).toEqual({
      name: "The Crown",
      type: "title",
      relationship: "actor",
      character: "Queen Elizabeth",
    });
  });

  it("drops character when relationship isn't actor, instead of rejecting the response", () => {
    const packet = validPacket({
      people: [
        {
          name: "Jane Doe",
          related_to: [{ name: "The Crown", type: "title", relationship: "director", character: "Queen Elizabeth" }],
        },
      ],
    });
    const result = parseArticleMentions(packet);
    expect(result.people[0]!.relatedTo[0]!.character).toBeNull();
  });

  it("does not constrain relationship vocabulary for company or person targets", () => {
    const packet = validPacket({
      people: [
        {
          name: "Jane Doe",
          related_to: [
            { name: "Netflix", type: "company", relationship: "signed with" },
            { name: "John Smith", type: "person", relationship: "co-writing with" },
          ],
        },
      ],
    });
    const result = parseArticleMentions(packet);
    expect(result.people[0]!.relatedTo).toEqual([
      { name: "Netflix", type: "company", relationship: "signed with", character: null },
      { name: "John Smith", type: "person", relationship: "co-writing with", character: null },
    ]);
  });

  it("trims whitespace and normalizes empty hint strings to null", () => {
    const packet = validPacket({
      people: [{ name: "  Jane Doe  ", role_hint: "  ", related_to: [] }],
    });
    const result = parseArticleMentions(packet);
    expect(result.people[0]!.name).toBe("Jane Doe");
    expect(result.people[0]!.roleHint).toBeNull();
  });

  // Real LLM response, captured from a live call to DeepSeek v4 Flash via
  // OpenRouter — not hand-written. Confirms the v2 contract (controlled
  // relationship vocabulary + separate character field) survives a real
  // model, and that co-star names don't leak into another person's
  // relatedTo entries.
  it("parses a real captured LLM response", () => {
    const raw = JSON.parse(
      readFileSync(resolve(__dirname, "__fixtures__/article-mentions/real-llm-response.json"), "utf-8"),
    );
    const result = parseArticleMentions(raw);

    expect(result.people).toHaveLength(4);
    expect(result.titles).toHaveLength(3);

    const janeDoe = result.people.find((p) => p.name === "Jane Doe");
    expect(janeDoe).toBeDefined();
    expect(janeDoe!.relatedTo).toContainEqual({
      name: "The Crown",
      type: "title",
      relationship: "actor",
      character: "Detective Reyes",
    });
    expect(janeDoe!.relatedTo).toContainEqual({
      name: "The Long Winter",
      type: "title",
      relationship: "director",
      character: null,
    });

    // Nicole Kidman and Judy Davis are their own independent people entries
    // with their own "actor" credit — not name-dropped inside Jane Doe's.
    const kidman = result.people.find((p) => p.name === "Nicole Kidman");
    expect(kidman!.relatedTo).toContainEqual({
      name: "The Long Winter",
      type: "title",
      relationship: "actor",
      character: null,
    });
  });
});
