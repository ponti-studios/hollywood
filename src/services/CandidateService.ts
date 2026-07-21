import { z } from '@hono/zod-openapi';
import { CreditRepository } from '../domain/repositories/CreditRepository.js';
import { EntityRepository, makeStableId } from '../domain/repositories/EntityRepository.js';
import { TagRepository } from '../domain/repositories/TagRepository.js';

// ── API schemas (source of truth for both the OpenAPI route and this service) ─

const CandidateCreditSchema = z.object({
  id: z.string(),
  role: z.string(),
  type: z.string().nullable(),
  production: z.string(),
  network: z.string().nullable(),
});

const CandidateEmailSchema = z.object({
  address: z.string(),
  contactType: z.string().nullable(),
});

const CandidatePhoneNumberSchema = z.object({
  number: z.string(),
  contactType: z.string().nullable(),
});

const CandidateRepresentativeSchema = z.object({
  id: z.string(),
  name: z.string(),
  organization: z.string(),
  representationType: z.string().nullable(),
  emails: z.array(CandidateEmailSchema),
  phoneNumbers: z.array(CandidatePhoneNumberSchema),
});

const CandidateTagSchema = z.object({
  id: z.string(),
  label: z.string(),
  tagger: z.string(),
});

const CandidateLinkSchema = z.object({
  url: z.string(),
  linkType: z.string(),
});

export const CandidateSchema = z.object({
  id: z.string(),
  name: z.string(),
  agencyBio: z.string().nullable(),
  position: z.string(),
  status: z.string(),
  credits: z.array(CandidateCreditSchema),
  emails: z.array(CandidateEmailSchema),
  phoneNumbers: z.array(CandidatePhoneNumberSchema),
  tags: z.array(CandidateTagSchema),
  representatives: z.array(CandidateRepresentativeSchema),
  links: z.array(CandidateLinkSchema),
});

export const CreateCandidateInputSchema = z.object({
  name: z.string().min(1),
  agencyBio: z.string().optional(),
  position: z.string().optional(),
  tags: z.array(z.string()).optional(),
  supportingLinks: z
    .array(
      z.object({
        url: z.string(),
        description: z.string().optional(),
        linkType: z.string().optional(),
      }),
    )
    .optional(),
});

export const UpdateCandidateInputSchema = z.object({
  name: z.string().optional(),
  agencyBio: z.string().optional(),
  position: z.string().optional(),
  status: z.string().optional(),
});

export type CandidateDetail = z.infer<typeof CandidateSchema>;
export type CreateCandidateInput = z.infer<typeof CreateCandidateInputSchema>;
export type UpdateCandidateInput = z.infer<typeof UpdateCandidateInputSchema>;

export class CandidateService {
  private entityRepo: EntityRepository;
  private creditRepo: CreditRepository;
  private tagRepo: TagRepository;

  constructor(opts?: {
    entityRepo?: EntityRepository;
    creditRepo?: CreditRepository;
    tagRepo?: TagRepository;
  }) {
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
    this.creditRepo = opts?.creditRepo ?? new CreditRepository();
    this.tagRepo = opts?.tagRepo ?? new TagRepository();
  }

  list(limit = 50, offset = 0): CandidateDetail[] {
    const rows = this.entityRepo.findByType('person', limit, offset);
    return rows.map((row) => this.enrich(row));
  }

  get(id: string): CandidateDetail | null {
    const row = this.entityRepo.findById(id);
    if (!row || row.entityType !== 'person') return null;
    return this.enrich(row);
  }

  create(inputs: CreateCandidateInput[]): CandidateDetail[] {
    const results: CandidateDetail[] = [];
    for (const input of inputs) {
      const entityId = makeStableId('entity', 'hollywood-api', input.name);
      const now = new Date().toISOString();

      this.entityRepo.insertWithId(entityId, {
        sourceId: 'hollywood-api',
        entityType: 'person',
        name: input.name,
        canonicalName: input.name.toLowerCase(),
        bio: input.agencyBio ?? null,
        position: input.position ?? null,
      });

      this.entityRepo.addAlias(entityId, 'hollywood-api', input.name);

      if (input.tags) {
        for (const tagText of input.tags) {
          const tag = this.tagRepo.ensure(tagText);
          this.tagRepo.tagEntity(entityId, tag.id, 'hollywood-api');
        }
      }

      if (input.supportingLinks) {
        for (const link of input.supportingLinks) {
          this.entityRepo.addLink(entityId, 'hollywood-api', link.url, link.linkType ?? 'other');
        }
      }

      results.push(
        this.enrich({
          id: entityId,
          name: input.name,
          bio: input.agencyBio ?? null,
          position: input.position ?? '',
          status: 'active',
        }),
      );
    }
    return results;
  }

  update(id: string, input: UpdateCandidateInput): CandidateDetail | null {
    const existing = this.entityRepo.findById(id);
    if (!existing || existing.entityType !== 'person') return null;

    this.entityRepo.update(id, {
      name: input.name,
      canonicalName: input.name ? input.name.toLowerCase() : undefined,
      bio: input.agencyBio !== undefined ? input.agencyBio : undefined,
      position: input.position,
      status: input.status,
    });

    const updated = this.entityRepo.findById(id)!;
    return this.enrich(updated);
  }

  delete(id: string): boolean {
    if (!this.entityRepo.exists(id)) return false;
    this.entityRepo.delete(id);
    return true;
  }

  totalCount(): number {
    return this.entityRepo.countByType('person');
  }

  // ── Private ──────────────────────────────────────────────────────────────

  private enrich(row: {
    id: string;
    name: string;
    bio: string | null;
    position: string | null;
    status: string | null;
    metadataJson?: string | null;
  }): CandidateDetail {
    const entityId = row.id;
    const credits = this.creditRepo.findByPerson(entityId);
    const aliases = this.entityRepo.findAliases(entityId);
    const contacts = this.entityRepo.findContacts(entityId);
    const tags = this.tagRepo.findByEntity(entityId);
    const reps = this.entityRepo.findRepresentatives(entityId);

    return {
      id: entityId,
      name: row.name,
      agencyBio: row.bio ?? null,
      position: row.position ?? '',
      status: row.status ?? 'active',
      credits: credits.map((c) => ({
        id: c.id,
        role: c.role,
        type: c.creditCategory ?? null,
        production: c.titleName ?? 'Unknown',
        network: null,
      })),
      emails: contacts
        .filter((c) => c.contactType === 'email')
        .map((c) => ({ address: c.contactValue, contactType: 'email' })),
      phoneNumbers: contacts
        .filter((c) => c.contactType === 'phone')
        .map((c) => ({ number: c.contactValue, contactType: 'phone' })),
      tags: tags.map((t) => ({ id: t.id, label: t.tag, tagger: 'system' })),
      representatives: reps.map((r) => ({
        id: r.id,
        name: '',
        organization: '',
        representationType: r.repType,
        emails: r.email ? [{ address: r.email, contactType: 'work' as const }] : [],
        phoneNumbers: r.phone ? [{ number: r.phone, contactType: 'work' as const }] : [],
      })),
      links: this.entityRepo.findLinks(entityId).map((l) => ({ url: l.url, linkType: l.linkType })),
    };
  }
}
