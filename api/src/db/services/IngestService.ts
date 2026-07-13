import { RunRepository, type RunStatus } from "../repositories/RunRepository.js";
import { RawRecordRepository } from "../repositories/RawRecordRepository.js";
import { EntityRepository, makeStableId } from "../repositories/EntityRepository.js";
import { CreditRepository } from "../repositories/CreditRepository.js";
import { TagRepository } from "../repositories/TagRepository.js";
import { ArticleRepository } from "../repositories/ArticleRepository.js";
import { ExtractionRepository } from "../repositories/ExtractionRepository.js";

import type {
  Candidate,
} from "../../ingest/extraction.js";
import type {
  ArchivedPayload,
  NormalizedBundle,
  ArticleRow,
  ArticleContentRow,
  EntityRow,
  EntityAliasRow,
  ArticleEntityRow,
  CreditRow,
} from "../../ingest/models.js";
import type { DbRow } from "../index.js";

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

  finishRun(runId: string, status: RunStatus, summary: Record<string, unknown>, errorText?: string): void {
    this.runRepo.finish(runId, status, summary, errorText);
  }

  // ── Raw records ───────────────────────────────────────────────────────────

  insertExtractionRawRecord(runId: string, sourceId: string, contentPath: string, contentHash: string): string {
    const rawId = makeStableId("extraction_raw", runId, sourceId, contentHash);
    this.rawRecordRepo.insertOne({
      id: rawId,
      runId,
      sourceId,
      sourceKind: "upload",
      payloadType: "text/plain",
      contentPath,
      contentHash,
      contentType: "text/plain",
      fetchedAt: new Date().toISOString(),
      metadataJson: "{}",
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
      schemaVersion: "v1_submission_packet",
      promptVersion,
      modelName,
      status: "succeeded",
      rawJson,
      resultJson: JSON.stringify(candidate),
    });
  }

  // ── Candidate materialization ─────────────────────────────────────────────

  materializeCandidate(candidate: Candidate, sourceId = "llm_extraction"): string {
    const entityId = this.entityRepo.upsert({
      sourceId,
      entityType: "person",
      name: candidate.name,
      canonicalName: candidate.name.toLowerCase(),
      bio: candidate.bio,
      position: candidate.position ?? "",
      licenseClass: "public",
    });

    this.entityRepo.addAlias(entityId, sourceId, candidate.name);

    if (candidate.email) {
      this.entityRepo.addContact(entityId, sourceId, "email", candidate.email);
    }
    if (candidate.phone_number) {
      this.entityRepo.addContact(entityId, sourceId, "phone", candidate.phone_number);
    }

    for (const credit of candidate.credits) {
      const titleId = this.entityRepo.upsert({
        sourceId,
        entityType: "title",
        name: credit.production,
        canonicalName: credit.production.toLowerCase(),
        titleType: "tv",
        licenseClass: "public",
      });

      this.creditRepo.upsert({
        personId: entityId,
        titleId,
        sourceId,
        role: credit.role,
        creditType: credit.type || "crew",
      });
    }

    for (const org of candidate.organizations) {
      this.entityRepo.upsert({
        sourceId,
        entityType: "company",
        name: org.name,
        canonicalName: org.name.toLowerCase(),
        companyType: org.type || "organization",
        licenseClass: "public",
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
        entityType: "person",
        name: rep.name,
        canonicalName: rep.name.toLowerCase(),
        companyType: "agent",
        licenseClass: "public",
      });

      const repRelId = makeStableId("rep", entityId, repEntityId);
      this.entityRepo.upsertRepresentation(
        repRelId,
        entityId,
        repEntityId,
        rep.title,
        rep.title,
        rep.email ?? "",
        rep.phone_number ?? "",
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

  loadRawRecords(opts: { sourceId?: string; runId?: string } = {}): DbRow[] {
    // Drizzle returns camelCase keys; adapters expect snake_case keys
    const rows = this.rawRecordRepo.find(opts);
    return rows.map((r) => this.toSnakeCase(r)) as unknown as DbRow[];
  }

  /** Convert Drizzle camelCase raw record to snake_case for adapter compatibility. */
  private toSnakeCase(r: Record<string, unknown>): Record<string, unknown> {
    const map: Record<string, string> = {
      id: "id",
      runId: "run_id",
      sourceId: "source_id",
      sourceKind: "source_kind",
      payloadType: "payload_type",
      contentPath: "content_path",
      contentHash: "content_hash",
      contentType: "content_type",
      sourceUrl: "source_url",
      canonicalUrl: "canonical_url",
      fetchedAt: "fetched_at",
      metadataJson: "metadata_json",
    };
    const result: Record<string, unknown> = {};
    for (const [camel, snake] of Object.entries(map)) {
      if (camel in r) result[snake] = r[camel];
    }
    return result;
  }

  // ── Normalized bundle ─────────────────────────────────────────────────────

  applyBundle(bundle: NormalizedBundle): void {
    this.upsertArticles(bundle.articles);
    this.upsertArticleContent(bundle.articleContent);
    this.upsertEntities(bundle.entities);
    this.upsertEntityAliases(bundle.entityAliases);
    this.upsertArticleEntities(bundle.articleEntities);
    this.upsertCredits(bundle.credits);
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
        licenseClass: r.licenseClass,
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
        licenseClass: r.licenseClass,
        metadataJson: r.metadataJson,
      });
    }
  }

  private upsertEntities(rows: EntityRow[]): void {
    for (const r of rows) {
      this.entityRepo.insertWithId(r.entityId, {
        sourceId: r.sourceId,
        externalId: r.externalId,
        entityType: r.entityType,
        name: r.name,
        canonicalName: r.canonicalName,
        licenseClass: r.licenseClass,
        metadataJson: r.metadataJson,
        titleType: r.titleType,
      });
    }
  }

  private upsertEntityAliases(rows: EntityAliasRow[]): void {
    for (const r of rows) {
      this.entityRepo.addAlias(r.entityId, r.sourceId, r.alias);
    }
  }

  private upsertArticleEntities(rows: ArticleEntityRow[]): void {
    for (const r of rows) {
      this.articleRepo.linkEntity({
        articleEntityId: r.articleEntityId,
        articleId: r.articleId,
        entityId: r.entityId,
        sourceId: r.sourceId,
        relation: r.relation,
        metadataJson: r.metadataJson,
      });
    }
  }

  private upsertCredits(rows: CreditRow[]): void {
    for (const r of rows) {
      if (r.personEntityId && r.titleEntityId) {
        this.creditRepo.upsert({
          personId: r.personEntityId,
          titleId: r.titleEntityId,
          sourceId: r.sourceId,
          role: r.role,
          billing: r.billing,
        });
      }
    }
  }
}
