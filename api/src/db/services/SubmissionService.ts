import { z } from '@hono/zod-openapi';
import { EntityRepository, makeStableId } from '../repositories/EntityRepository.js';
import {
  SubmissionRepository,
  type SubmissionFields,
} from '../repositories/SubmissionRepository.js';

// ── API schemas (source of truth for both the OpenAPI route and this service) ─

const SubmissionCreditSchema = z.object({
  role: z.string().nullable(),
  type: z.string().nullable(),
  production: z.string().nullable(),
  network: z.string().nullable(),
});

const SubmissionRepresentativeSchema = z.object({
  name: z.string().nullable(),
  title: z.string().nullable(),
  agency: z.string().nullable(),
  email: z.string().nullable(),
});

const SubmissionLinkSchema = z.object({
  url: z.string().nullable(),
  type: z.string().nullable(),
});

const SubmissionJsonSchema = z.object({
  name: z.string(),
  bio: z.string().nullable(),
  email: z.string().nullable(),
  phoneNumber: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
  organizations: z.array(z.string()).nullable(),
  credits: z.array(SubmissionCreditSchema).nullable(),
  representatives: z.array(SubmissionRepresentativeSchema).nullable(),
  links: z.array(SubmissionLinkSchema).nullable(),
  attachments: z.array(z.string()).nullable(),
});

export const SubmissionSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  candidateId: z.string().nullable(),
  created: z.string(),
  submissionJson: SubmissionJsonSchema,
  samples: z.array(z.unknown()),
  rawSamples: z.array(z.unknown()),
});

export type SubmissionDetail = z.infer<typeof SubmissionSchema>;

export class SubmissionService {
  private submissionRepo: SubmissionRepository;
  private entityRepo: EntityRepository;

  constructor(opts?: { submissionRepo?: SubmissionRepository; entityRepo?: EntityRepository }) {
    this.submissionRepo = opts?.submissionRepo ?? new SubmissionRepository();
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
  }

  list(projectId?: string): SubmissionDetail[] {
    const rows = this.submissionRepo.findAllWithExtractions();
    return rows.map((r) => ({
      id: r.id,
      projectId: projectId ?? 'default',
      candidateId: null,
      created: r.createdAt,
      // parseResultJson is a best-effort passthrough of whatever JSON the
      // extraction actually stored — it doesn't strictly conform to
      // SubmissionJsonSchema in every branch (e.g. the non-candidate-packet
      // fallback returns the raw parsed object as-is). Pre-existing
      // behavior, not introduced by this cast.
      submissionJson: this.parseResultJson(r.resultJson) as SubmissionDetail['submissionJson'],
      samples: [],
      rawSamples: [],
    }));
  }

  delete(id: string): { deleted: boolean } {
    const existing = this.submissionRepo.findById(id);
    if (!existing) return { deleted: false };
    const changes = this.submissionRepo.delete(id);
    return { deleted: changes > 0 };
  }

  createCandidate(
    submissionId: string,
    position: string,
  ): { id: string; name: string; position: string; status: string } | null {
    const sub = this.submissionRepo.findWithExtraction(submissionId);
    if (!sub) return null;

    const sj = this.parseResultJson(sub.resultJson ?? null);
    const name = (sj.name as string) ?? 'Unknown';
    const entityId = makeStableId('entity', 'hollywood-api', name);
    const now = new Date().toISOString();

    this.entityRepo.insertWithId(entityId, {
      sourceId: 'hollywood-api',
      entityType: 'person',
      name,
      canonicalName: name.toLowerCase(),
      bio: (sj.bio as string) ?? null,
      position: position,
    });

    this.entityRepo.addAlias(entityId, 'hollywood-api', name);

    return { id: entityId, name, position, status: 'active' };
  }

  private parseResultJson(raw: string | null): Record<string, unknown> {
    if (!raw) return { name: 'Unknown' };
    try {
      const obj = JSON.parse(raw);
      // SubmissionPacket format: { candidates: [{ name, bio, ... }] }
      if (obj.candidates && Array.isArray(obj.candidates) && obj.candidates.length > 0) {
        const c = obj.candidates[0];
        return {
          name: c.name ?? 'Unknown',
          bio: c.bio ?? null,
          email: c.email ?? null,
          phone_number: c.phone_number ?? null,
          tags: c.tags ?? [],
          organizations: (c.organizations ?? []).map((o: Record<string, unknown>) => o.name),
          credits: (c.credits ?? []).map((cr: Record<string, unknown>) => ({
            role: cr.role ?? null,
            type: cr.type ?? null,
            production: cr.production ?? null,
          })),
          representatives: (c.representatives ?? []).map((rep: Record<string, unknown>) => ({
            name: rep.name ?? null,
            title: rep.title ?? null,
          })),
          links: (c.links ?? []).map((l: Record<string, unknown>) => ({
            url: l.url ?? null,
            type: l.type ?? null,
          })),
        };
      }
      return obj;
    } catch {
      return { name: 'Unknown' };
    }
  }
}
