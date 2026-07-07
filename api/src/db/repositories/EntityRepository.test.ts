import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { setupTestDb } from "../test-utils.js";
import { EntityRepository, makeStableId } from "./EntityRepository.js";

describe("EntityRepository", () => {
  let repo: EntityRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    repo = new EntityRepository(test.db);
    cleanup = test.cleanup;
  });

  afterEach(() => {
    cleanup();
  });

  describe("CRUD", () => {
    it("creates and finds a person entity", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alyson Fouse",
        canonicalName: "alyson fouse",
        bio: "Writer and producer",
        position: "writer",
        licenseClass: "public",
      });

      const found = repo.findById(id);
      expect(found).not.toBeNull();
      expect(found!.name).toBe("Alyson Fouse");
      expect(found!.entityType).toBe("person");
      expect(found!.bio).toBe("Writer and producer");
      expect(found!.position).toBe("writer");
      expect(found!.status).toBe("active");
      expect(found!.licenseClass).toBe("public");
    });

    it("upsert is idempotent — does not overwrite on conflict", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alyson Fouse",
        canonicalName: "alyson fouse",
        licenseClass: "public",
      });

      const id2 = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alyson Fouse",
        canonicalName: "alyson fouse",
        bio: "Different bio",
        licenseClass: "public",
      });

      expect(id).toBe(id2);
      const found = repo.findById(id);
      expect(found!.bio).toBeNull();
    });

    it("upsertReplace overwrites on conflict", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alyson Fouse",
        canonicalName: "alyson fouse",
        licenseClass: "public",
      });

      const id2 = repo.upsertReplace({
        sourceId: "test",
        entityType: "person",
        name: "Alyson Fouse",
        canonicalName: "alyson fouse",
        bio: "Replaced bio",
        licenseClass: "public",
      });

      expect(id).toBe(id2);
      const found = repo.findById(id);
      expect(found!.bio).toBe("Replaced bio");
    });

    it("insertWithId uses the provided ID", () => {
      repo.insertWithId("custom-id-123", {
        sourceId: "test",
        entityType: "person",
        name: "Custom ID Person",
        canonicalName: "custom id person",
        licenseClass: "public",
      });

      const found = repo.findById("custom-id-123");
      expect(found).not.toBeNull();
      expect(found!.name).toBe("Custom ID Person");
    });

    it("finds by type", () => {
      repo.upsert({ sourceId: "test", entityType: "person", name: "Alice", canonicalName: "alice", licenseClass: "public" });
      repo.upsert({ sourceId: "test", entityType: "person", name: "Bob", canonicalName: "bob", licenseClass: "public" });
      repo.upsert({ sourceId: "test", entityType: "title", name: "THE SHOW", canonicalName: "the show", licenseClass: "public" });

      const persons = repo.findByType("person");
      expect(persons).toHaveLength(2);
      expect(persons.map((p) => p.name).sort()).toEqual(["Alice", "Bob"]);
    });

    it("updates entity fields", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alice",
        canonicalName: "alice",
        licenseClass: "public",
      });

      repo.update(id, { name: "Alice Smith", canonicalName: "alice smith", bio: "Updated bio" });

      const found = repo.findById(id);
      expect(found!.name).toBe("Alice Smith");
      expect(found!.canonicalName).toBe("alice smith");
      expect(found!.bio).toBe("Updated bio");
    });

    it("deletes entity", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "To Delete",
        canonicalName: "to delete",
        licenseClass: "public",
      });

      expect(repo.exists(id)).toBe(true);
      repo.delete(id);
      expect(repo.exists(id)).toBe(false);
      expect(repo.findById(id)).toBeNull();
    });

    it("checks existence", () => {
      expect(repo.exists("nonexistent")).toBe(false);

      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Exists",
        canonicalName: "exists",
        licenseClass: "public",
      });

      expect(repo.exists(id)).toBe(true);
    });
  });

  describe("search", () => {
    beforeEach(() => {
      repo.upsert({ sourceId: "test", entityType: "person", name: "Alyson Fouse", canonicalName: "alyson fouse", licenseClass: "public" });
      repo.upsert({ sourceId: "test", entityType: "person", name: "John Smith", canonicalName: "john smith", licenseClass: "public" });
      repo.upsert({ sourceId: "test", entityType: "title", name: "ALYSON'S SHOW", canonicalName: "alyson's show", licenseClass: "public" });
      repo.upsert({ sourceId: "test", entityType: "person", name: "Jane Doe", canonicalName: "jane doe", licenseClass: "public" });
    });

    it("searches by name with LIKE", () => {
      const { rows, total } = repo.searchByName("Alyson");
      expect(total).toBe(2);
      expect(rows.map((r) => r.name).sort()).toEqual(["ALYSON'S SHOW", "Alyson Fouse"]);
    });

    it("returns zero results for non-matching query", () => {
      const { rows, total } = repo.searchByName("Zzzzzz");
      expect(total).toBe(0);
      expect(rows).toHaveLength(0);
    });

    it("respects limit and offset", () => {
      const { rows, total } = repo.searchByName("o", 1, 0);
      // "o" matches: Alyson Fouse, John Smith, ALYSON'S SHOW, Jane Doe = 4
      expect(total).toBe(4);
      expect(rows).toHaveLength(1);
    });
  });

  describe("aliases", () => {
    it("adds and finds aliases", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alice",
        canonicalName: "alice",
        licenseClass: "public",
      });

      repo.addAlias(id, "test", "Alice A.");
      repo.addAlias(id, "test", "A. Smith");

      const aliases = repo.findAliases(id);
      expect(aliases).toHaveLength(2);
      expect(aliases.map((a) => a.alias).sort()).toEqual(["A. Smith", "Alice A."]);
    });

    it("alias upsert is idempotent", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Alice",
        canonicalName: "alice",
        licenseClass: "public",
      });

      const a1 = repo.addAlias(id, "test", "Alice");
      const a2 = repo.addAlias(id, "test", "Alice");
      expect(a1).toBe(a2);
      expect(repo.findAliases(id)).toHaveLength(1);
    });
  });

  describe("contacts", () => {
    it("adds and finds contacts by type", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Bob",
        canonicalName: "bob",
        licenseClass: "public",
      });

      repo.addContact(id, "test", "email", "bob@example.com");
      repo.addContact(id, "test", "phone", "+1-555-0100");

      const allContacts = repo.findContacts(id);
      expect(allContacts).toHaveLength(2);

      const emails = repo.findContacts(id, "email");
      expect(emails).toHaveLength(1);
      expect(emails[0].contactValue).toBe("bob@example.com");
    });
  });

  describe("links", () => {
    it("adds and finds links", () => {
      const id = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Charlie",
        canonicalName: "charlie",
        licenseClass: "public",
      });

      repo.addLink(id, "test", "https://imdb.com/name/nm123", "imdb");
      repo.addLink(id, "test", "https://twitter.com/charlie", "twitter");

      const links = repo.findLinks(id);
      expect(links).toHaveLength(2);
      expect(links.map((l) => l.linkType).sort()).toEqual(["imdb", "twitter"]);
    });
  });

  describe("stable IDs", () => {
    it("same source + name produces same ID", () => {
      const id1 = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Jane Doe",
        canonicalName: "jane doe",
        licenseClass: "public",
      });

      const id2 = repo.upsert({
        sourceId: "test",
        entityType: "person",
        name: "Jane Doe",
        canonicalName: "jane doe",
        licenseClass: "public",
      });

      expect(id1).toBe(id2);
    });

    it("different sources produce different IDs for same name", () => {
      const id1 = repo.upsert({
        sourceId: "source_a",
        entityType: "person",
        name: "Jane Doe",
        canonicalName: "jane doe",
        licenseClass: "public",
      });

      const id2 = repo.upsert({
        sourceId: "source_b",
        entityType: "person",
        name: "Jane Doe",
        canonicalName: "jane doe",
        licenseClass: "public",
      });

      expect(id1).not.toBe(id2);
    });

    it("makeStableId produces consistent hashes", () => {
      expect(makeStableId("entity", "test", "Alice")).toBe(makeStableId("entity", "test", "Alice"));
      expect(makeStableId("entity", "test", "Alice")).not.toBe(makeStableId("entity", "test", "Bob"));
    });
  });
});
