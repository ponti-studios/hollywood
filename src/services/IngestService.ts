import type { Candidate } from '../enrichment/submissions/extraction.js';
import type {
  ArchivedPayload,
  NormalizedBundle,
  ArticleRow,
  ArticleContentRow,
  EntityRow,
  EntityAliasRow,
  ArticleEntityRow,
  CreditRow,
} from '../ingestion/models.js';
import { ArticleRepository } from '../domain/repositories/ArticleRepository.js';
import { CreditRepository } from '../domain/repositories/CreditRepository.js';
import { EntityRepository, makeStableId } from '../domain/repositories/EntityRepository.js';
import { ExtractionRepository } from '../domain/repositories/ExtractionRepository.js';
import { RawRecordRepository, type RawRecordRow } from '../domain/repositories/RawRecordRepository.js';
import { RunRepository, type RunStatus } from '../domain/repositories/RunRepository.js';
import { TagRepository } from '../domain/repositories/TagRepository.js';

export class IngestService {
  private runRepo: RunRepository;
  private rawRecordRepo: RawRecordRepository;
  private entityRepo: EntityRepository;
  private creditRepo: CreditRepository;
  private tagRepo: TagRepository;
  private articleRepo: ArticleRepository;
  private extractionRepo: ExtractionRepository;

  constructor(opts?: {
    runRepo?: RunRepository;
    rawRecordRepo?: RawRecordRepository;
    entityRepo?: EntityRepository;
    creditRepo?: CreditRepository;
    tagRepo?: TagRepository;
    articleRepo?: ArticleRepository;
    extractionRepo?: ExtractionRepository;
  }) {
    this.runRepo = opts?.runRepo ?? new RunRepository();
    this.rawRecordRepo = opts?.rawRecordRepo ?? new RawRecordRepository();
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
    this.creditRepo = opts?.creditRepo ?? new CreditRepository();
    this.tagRepo = opts?.tagRepo ?? new TagRepository();
    this.articleRepo = opts?.articleRepo ?? new ArticleRepository();
    this.extractionRepo = opts?.extractionRepo ?? new ExtractionRepository();
  }

  // ── Run tracking ──────────────────────────────────────────────────────────

  startRun(sourceId: string, optionsJson: string): string {
    return this.runRepo.start(sourceId, optionsJson);
  }

  startRunRaw(runKind: string, metadata: Record<string, unknown>): string {
    return this.runRepo.startRaw(runKind, metadata);
  }

  finishRun(
    runId: string,
    status: RunStatus,
    summary: object,
    errorText?: string,
  ): void {
    this.runRepo.finish(runId, status, summary, errorText);
  }

  // ── Raw records ───────────────────────────────────────────────────────────

  insertExtractionRawRecord(
    runId: string,
    sourceId: string,
    contentPath: string,
    contentHash: string,
  ): string {
    const rawId = makeStableId('extraction_raw', runId, sourceId, contentHash);
    this.rawRecordRepo.insertOne({
      id: rawId,
      runId,
      sourceId,
      sourceKind: 'upload',
      payloadType: 'text/plain',
      contentPath,
      contentHash,
      contentType: 'text/plain',
      fetchedAt: new Date().toISOString(),
      metadataJson: '{}',
    });
    return rawId;
  }

  saveExtractionResult(
    runId: string,
    sourceId: string,
    candidate: Candidate,
    modelName: string,
    promptVersion: string,
    rawJson: string,
    rawRecordId?: string,
  ): void {
    const docId = rawRecordId ?? runId;
    this.extractionRepo.save({
      documentId: docId,
      jobId: runId,
      schemaVersion: 'v1_submission_packet',
      promptVersion,
      modelName,
      status: 'succeeded',
      rawJson,
      resultJson: JSON.stringify(candidate),
    });
  }

  // ── Candidate materialization ─────────────────────────────────────────────

  materializeCandidate(candidate: Candidate, sourceId = 'llm_extraction'): string {
    const entityId = this.entityRepo.upsert({
      sourceId,
      entityType: 'person',
      name: candidate.name,
      canonicalName: candidate.name.toLowerCase(),
      bio: candidate.bio,
      position: candidate.position ?? '',
    });

    this.entityRepo.addAlias(entityId, sourceId, candidate.name);

    if (candidate.email) {
      this.entityRepo.addContact(entityId, sourceId, 'email', candidate.email);
    }
    if (candidate.phone_number) {
      this.entityRepo.addContact(entityId, sourceId, 'phone', candidate.phone_number);
    }

    for (const credit of candidate.credits) {
      const titleId = this.entityRepo.upsert({
        sourceId,
        entityType: 'title',
        name: credit.production,
        canonicalName: credit.production.toLowerCase(),
        titleType: 'tv',
      });

      this.creditRepo.upsert({
        personId: entityId,
        titleId,
        sourceId,
        role: credit.role,
        creditCategory: credit.type || 'crew',
      });
    }

    for (const org of candidate.organizations) {
      this.entityRepo.upsert({
        sourceId,
        entityType: 'company',
        name: org.name,
        canonicalName: org.name.toLowerCase(),
        companyType: org.type || 'organization',
      });
    }

    for (const tagText of candidate.tags) {
      const tag = this.tagRepo.ensure(tagText);
      this.tagRepo.tagEntity(entityId, tag.id, sourceId);
    }

    for (const link of candidate.links) {
      this.entityRepo.addLink(entityId, sourceId, link.url, link.type);
    }

    for (const rep of candidate.representatives) {
      const repEntityId = this.entityRepo.upsert({
        sourceId,
        entityType: 'person',
        name: rep.name,
        canonicalName: rep.name.toLowerCase(),
        companyType: 'agent',
      });

      const repRelId = makeStableId('rep', entityId, repEntityId);
      this.entityRepo.upsertRepresentation(
        repRelId,
        entityId,
        repEntityId,
        rep.title,
        rep.title,
        rep.email ?? '',
        rep.phone_number ?? '',
        sourceId,
      );
    }

    return entityId;
  }

  // ── Raw record batches ────────────────────────────────────────────────────

  insertRawRecords(runId: string, archivedPayloads: ArchivedPayload[]): void {
    const records = archivedPayloads.map((p) => ({
      id: p.rawRecordId,
      runId,
      sourceId: p.sourceId,
      sourceKind: p.sourceKind,
      payloadType: p.payloadType,
      contentPath: p.contentPath,
      contentHash: p.contentHash,
      contentType: p.contentType,
      sourceUrl: p.sourceUrl ?? null,
      canonicalUrl: p.canonicalUrl ?? null,
      fetchedAt: p.fetchedAt.toISOString(),
      metadataJson: p.metadataJson,
    }));
    this.rawRecordRepo.insertBatch(records);
  }

  loadRawRecords(opts: { sourceId?: string; runId?: string } = {}): RawRecordRow[] {
    return this.rawRecordRepo.find(opts);
  }

  // ── Normalized bundle ─────────────────────────────────────────────────────

  applyBundle(bundle: NormalizedBundle): { entitiesMatched: number; entitiesCreated: number } {
    this.upsertArticles(bundle.articles);
    this.upsertArticleContent(bundle.articleContent);
    const remap = this.upsertEntities(bundle.entities);
    this.upsertEntityAliases(bundle.entityAliases, remap);
    this.upsertArticleEntities(bundle.articleEntities, remap);
    this.upsertCredits(bundle.credits, remap);

    let entitiesMatched = 0;
    for (const [precomputed, resolved] of remap) {
      if (precomputed !== resolved) entitiesMatched++;
    }
    return { entitiesMatched, entitiesCreated: remap.size - entitiesMatched };
  }

  private upsertArticles(rows: ArticleRow[]): void {
    for (const r of rows) {
      this.articleRepo.upsertArticle({
        articleId: r.articleId,
        sourceId: r.sourceId,
        canonicalUrl: r.canonicalUrl,
        url: r.url,
        title: r.title,
        author: r.author ?? null,
        publishedAt: r.publishedAt?.toISOString() ?? null,
        summary: r.summary ?? null,
        feedGuid: r.feedGuid ?? null,
        runId: r.runId,
        metadataJson: r.metadataJson,
      });
    }
  }

  private upsertArticleContent(rows: ArticleContentRow[]): void {
    for (const r of rows) {
      this.articleRepo.upsertContent({
        contentId: r.contentId,
        articleId: r.articleId,
        sourceId: r.sourceId,
        contentKind: r.contentKind,
        text: r.text,
        rawRecordId: r.rawRecordId ?? null,
        contentHash: r.contentHash,
        metadataJson: r.metadataJson,
      });
    }
  }

  private upsertEntities(rows: EntityRow[]): Map<string, string> {
    const remap = new Map<string, string>();
    for (const r of rows) {
      const existing = this.entityRepo.findByCanonicalName(r.entityType, r.canonicalName);
      if (existing) {
        remap.set(r.entityId, existing.id);
        this.entityRepo.addAlias(existing.id, r.sourceId, r.name);
      } else {
        this.entityRepo.insertWithId(r.entityId, {
          sourceId: r.sourceId,
          externalId: r.externalId,
          entityType: r.entityType,
          name: r.name,
          canonicalName: r.canonicalName,
          metadataJson: r.metadataJson,
          titleType: r.titleType,
        });
        remap.set(r.entityId, r.entityId);
      }
    }
    return remap;
  }

  private upsertEntityAliases(rows: EntityAliasRow[], remap: Map<string, string>): void {
    for (const r of rows) {
      const resolvedId = remap.get(r.entityId) ?? r.entityId;
      this.entityRepo.addAlias(resolvedId, r.sourceId, r.alias);
    }
  }

  private upsertArticleEntities(rows: ArticleEntityRow[], remap: Map<string, string>): void {
    for (const r of rows) {
      const resolvedId = remap.get(r.entityId) ?? r.entityId;
      this.articleRepo.linkEntity({
        articleEntityId: r.articleEntityId,
        articleId: r.articleId,
        entityId: resolvedId,
        sourceId: r.sourceId,
        relation: r.relation,
        metadataJson: r.metadataJson,
      });
    }
  }

  private upsertCredits(rows: CreditRow[], remap: Map<string, string>): void {
    for (const r of rows) {
      if (r.personEntityId && r.titleEntityId) {
        const personId = remap.get(r.personEntityId) ?? r.personEntityId;
        const titleId = remap.get(r.titleEntityId) ?? r.titleEntityId;
        this.creditRepo.upsert({
          personId,
          titleId,
          sourceId: r.sourceId,
          role: r.role,
          creditCategory: r.creditCategory,
          billing: r.billing,
          metadataJson: r.metadataJson,
        });
      }
    }
  }
}
