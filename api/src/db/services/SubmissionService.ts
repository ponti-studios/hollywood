import { SubmissionRepository, type SubmissionFields } from "../repositories/SubmissionRepository.js";
import { EntityRepository, makeStableId } from "../repositories/EntityRepository.js";

export interface SubmissionDetail {
  id: string;
  projectId: string;
  candidateId: string | null;
  created: string;
  submissionJson: Record<string, unknown>;
  samples: unknown[];
  rawSamples: unknown[];
}

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
      projectId: projectId ?? "default",
      candidateId: null,
      created: r.createdAt,
      submissionJson: this.parseResultJson(r.resultJson),
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

  createCandidate(submissionId: string, position: string): { id: string; name: string; position: string; status: string } | null {
    const sub = this.submissionRepo.findWithExtraction(submissionId);
    if (!sub) return null;

    const sj = this.parseResultJson(sub.resultJson ?? null);
    const name = (sj.name as string) ?? "Unknown";
    const entityId = makeStableId("entity", "hollywood-api", name);
    const now = new Date().toISOString();

    this.entityRepo.insertWithId(entityId, {
      sourceId: "hollywood-api",
      entityType: "person",
      name,
      canonicalName: name.toLowerCase(),
      bio: (sj.bio as string) ?? null,
      position: position,
      licenseClass: "public",
    });

    this.entityRepo.addAlias(entityId, "hollywood-api", name);

    return { id: entityId, name, position, status: "active" };
  }

  private parseResultJson(raw: string | null): Record<string, unknown> {
    if (!raw) return { name: "Unknown" };
    try {
      const obj = JSON.parse(raw);
      // SubmissionPacket format: { candidates: [{ name, bio, ... }] }
      if (obj.candidates && Array.isArray(obj.candidates) && obj.candidates.length > 0) {
        const c = obj.candidates[0];
        return {
          name: c.name ?? "Unknown",
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
      return { name: "Unknown" };
    }
  }
}
