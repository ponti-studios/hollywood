import { EntityRepository, makeStableId } from "../repositories/EntityRepository.js";

export interface ProjectDetail {
  id: string;
  title: string;
  season: number;
  genres: string[];
  format: string | null;
  imdbLink: string | null;
  posterLink: string | null;
}

export interface CreateProjectInput {
  title: string;
  format?: string;
  genres?: string[];
  season?: number;
  imdbLink?: string;
}

export interface UpdateProjectInput {
  title?: string;
  format?: string;
  genres?: string[];
  season?: number;
  imdbLink?: string;
}

export class ProjectService {
  private entityRepo: EntityRepository;

  constructor(opts?: { entityRepo?: EntityRepository }) {
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
  }

  list(): ProjectDetail[] {
    const rows = this.entityRepo.findByTypes(["title", "project"]);
    return rows.map((row) => this.enrich(row));
  }

  get(id: string): ProjectDetail | null {
    const row = this.entityRepo.findById(id);
    if (!row || (row.entityType !== "title" && row.entityType !== "project")) return null;
    return this.enrich(row);
  }

  create(input: CreateProjectInput): ProjectDetail {
    const entityId = makeStableId("entity", "hollywood-api", input.title);
    const meta = JSON.stringify({
      genres: input.genres ?? [],
      season: input.season ?? 1,
      imdb_link: input.imdbLink ?? null,
    });
    const now = new Date().toISOString();

    this.entityRepo.insertWithId(entityId, {
      sourceId: "hollywood-api",
      externalId: input.imdbLink ?? null,
      entityType: "title",
      name: input.title,
      canonicalName: input.title.toLowerCase(),
      titleType: input.format ?? null,
      licenseClass: "public",
      metadataJson: meta,
    });

    return this.enrich({
      id: entityId,
      name: input.title,
      titleType: input.format ?? null,
      metadataJson: meta,
    } as any);
  }

  update(id: string, input: UpdateProjectInput): ProjectDetail | null {
    const existing = this.entityRepo.findById(id);
    if (!existing || (existing.entityType !== "title" && existing.entityType !== "project")) return null;

    // Parse existing metadata
    const existingMeta = existing.metadataJson ? JSON.parse(existing.metadataJson) : {};

    const inputGenres = input.genres ?? existingMeta.genres ?? [];
    const inputSeason = input.season ?? existingMeta.season ?? 1;
    const inputImdb = input.imdbLink ?? existingMeta.imdb_link ?? null;

    const meta = JSON.stringify({
      genres: inputGenres,
      season: inputSeason,
      imdb_link: inputImdb,
    });

    this.entityRepo.update(id, {
      name: input.title,
      canonicalName: input.title ? input.title.toLowerCase() : undefined,
      titleType: input.format,
      metadataJson: meta,
    });

    const updated = this.entityRepo.findById(id)!;
    return this.enrich(updated);
  }

  // ── Private ──────────────────────────────────────────────────────────────

  private enrich(row: { id: string; name: string; titleType: string | null; metadataJson: string | null }): ProjectDetail {
    const meta = row.metadataJson ? JSON.parse(row.metadataJson) : {};
    return {
      id: row.id,
      title: row.name,
      season: meta.season ?? 1,
      genres: meta.genres ?? [],
      format: row.titleType ?? null,
      imdbLink: meta.imdb_link ?? null,
      posterLink: meta.poster_link ?? null,
    };
  }
}
