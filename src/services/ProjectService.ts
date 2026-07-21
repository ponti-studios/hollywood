import { z } from '@hono/zod-openapi';
import { EntityRepository, makeStableId } from '../domain/repositories/EntityRepository.js';

// ── API schemas (source of truth for both the OpenAPI route and this service) ─

export const ProjectSchema = z.object({
  id: z.string(),
  title: z.string(),
  season: z.number().int(),
  genres: z.array(z.string()),
  format: z.string().nullable(),
  posterLink: z.string().nullable(),
});

export const CreateProjectSchema = z.object({
  title: z.string().min(1),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
});

export const UpdateProjectSchema = z.object({
  title: z.string().optional(),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
});

export type ProjectDetail = z.infer<typeof ProjectSchema>;
export type CreateProjectInput = z.infer<typeof CreateProjectSchema>;
export type UpdateProjectInput = z.infer<typeof UpdateProjectSchema>;

export class ProjectService {
  private entityRepo: EntityRepository;

  constructor(opts?: { entityRepo?: EntityRepository }) {
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
  }

  list(): ProjectDetail[] {
    const rows = this.entityRepo.findByType('title');
    return rows.map((row) => this.enrich(row));
  }

  get(id: string): ProjectDetail | null {
    const row = this.entityRepo.findById(id);
    if (!row || row.entityType !== 'title') return null;
    return this.enrich(row);
  }

  create(input: CreateProjectInput): ProjectDetail {
    const entityId = makeStableId('entity', 'hollywood-api', input.title);
    const meta = JSON.stringify({
      genres: input.genres ?? [],
      season: input.season ?? 1,
    });
    const now = new Date().toISOString();

    this.entityRepo.insertWithId(entityId, {
      sourceId: 'hollywood-api',
      externalId: null,
      entityType: 'title',
      name: input.title,
      canonicalName: input.title.toLowerCase(),
      titleType: input.format ?? null,
      metadataJson: meta,
    });

    return this.enrich({
      id: entityId,
      name: input.title,
      titleType: input.format ?? null,
      metadataJson: meta,
    });
  }

  update(id: string, input: UpdateProjectInput): ProjectDetail | null {
    const existing = this.entityRepo.findById(id);
    if (!existing || existing.entityType !== 'title') return null;

    const existingMeta = existing.metadataJson ? JSON.parse(existing.metadataJson) : {};

    const inputGenres = input.genres ?? existingMeta.genres ?? [];
    const inputSeason = input.season ?? existingMeta.season ?? 1;

    const meta = JSON.stringify({
      genres: inputGenres,
      season: inputSeason,
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

  private enrich(row: {
    id: string;
    name: string;
    titleType: string | null;
    metadataJson: string | null;
  }): ProjectDetail {
    const meta = row.metadataJson ? JSON.parse(row.metadataJson) : {};
    return {
      id: row.id,
      title: row.name,
      season: meta.season ?? 1,
      genres: meta.genres ?? [],
      format: row.titleType ?? null,
      posterLink: meta.poster_link ?? null,
    };
  }
}
