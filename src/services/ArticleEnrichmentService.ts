import { callOpenRouterForArticleMentions } from '../enrichment/article-mentions/article-mentions-llm.js';
import type { LlmProvider } from '../enrichment/article-mentions/article-mentions-llm.js';
import { SCHEMA_VERSION_V2, PROMPT_VERSION_V2 } from '../enrichment/article-mentions/article-mentions.js';
import type { ArticleMentions } from '../enrichment/article-mentions/article-mentions.js';
import { ArticleRepository } from '../domain/repositories/ArticleRepository.js';
import { CompanyRelationRepository } from '../domain/repositories/CompanyRelationRepository.js';
import { CreditRepository } from '../domain/repositories/CreditRepository.js';
import { EntityRepository, makeStableId } from '../domain/repositories/EntityRepository.js';
import { ExtractionRepository } from '../domain/repositories/ExtractionRepository.js';

const LLM_TRUST_STATE = 'llm_extracted';

export interface MaterializeMentionsParams {
  articleId: string;
  rawRecordId: string;
  mentions: ArticleMentions;
  sourceId: string;
  jobId?: string | null;
  promptVersion: string;
  modelName: string;
  rawJson: string;
}

export interface MaterializeMentionsResult {
  peopleCreated: number;
  peopleMatched: number;
  titlesCreated: number;
  titlesMatched: number;
  companiesCreated: number;
  companiesMatched: number;
  creditsCreated: number;
  companyRelationsCreated: number;
  mentionsRecorded: number;
}

export interface EnrichNextOptions {
  limit: number;
  promptVersion?: string;
  model?: string;
  provider?: LlmProvider;
}

export interface EnrichNextSummary extends MaterializeMentionsResult {
  articlesProcessed: number;
  articlesFailed: number;
}

type LlmCall = typeof callOpenRouterForArticleMentions;

export class ArticleEnrichmentService {
  private articleRepo: ArticleRepository;
  private entityRepo: EntityRepository;
  private creditRepo: CreditRepository;
  private companyRelationRepo: CompanyRelationRepository;
  private extractionRepo: ExtractionRepository;
  private llmCall: LlmCall;

  constructor(opts?: {
    articleRepo?: ArticleRepository;
    entityRepo?: EntityRepository;
    creditRepo?: CreditRepository;
    companyRelationRepo?: CompanyRelationRepository;
    extractionRepo?: ExtractionRepository;
    llmCall?: LlmCall;
  }) {
    this.articleRepo = opts?.articleRepo ?? new ArticleRepository();
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
    this.creditRepo = opts?.creditRepo ?? new CreditRepository();
    this.companyRelationRepo = opts?.companyRelationRepo ?? new CompanyRelationRepository();
    this.extractionRepo = opts?.extractionRepo ?? new ExtractionRepository();
    this.llmCall = opts?.llmCall ?? callOpenRouterForArticleMentions;
  }

  /** Writes an already-parsed ArticleMentions packet into the domain graph. Idempotent. */
  materializeMentions(params: MaterializeMentionsParams): MaterializeMentionsResult {
    const result: MaterializeMentionsResult = {
      peopleCreated: 0,
      peopleMatched: 0,
      titlesCreated: 0,
      titlesMatched: 0,
      companiesCreated: 0,
      companiesMatched: 0,
      creditsCreated: 0,
      companyRelationsCreated: 0,
      mentionsRecorded: 0,
    };

    const titleIds = new Map<string, string>();
    for (const title of params.mentions.titles) {
      const canonicalName = title.name.toLowerCase();
      const existing = this.entityRepo.findByCanonicalName('title', canonicalName);
      if (existing) {
        result.titlesMatched++;
        titleIds.set(canonicalName, existing.id);
      } else {
        const id = this.entityRepo.upsert({
          sourceId: params.sourceId,
          entityType: 'title',
          name: title.name,
          canonicalName,
          titleType: title.formatHint ?? undefined,
        });
        result.titlesCreated++;
        titleIds.set(canonicalName, id);
      }
    }

    const companyIds = new Map<string, string>();
    for (const company of params.mentions.companies) {
      const canonicalName = company.name.toLowerCase();
      const existing = this.entityRepo.findByCanonicalName('company', canonicalName);
      if (existing) {
        result.companiesMatched++;
        companyIds.set(canonicalName, existing.id);
      } else {
        const id = this.entityRepo.upsert({
          sourceId: params.sourceId,
          entityType: 'company',
          name: company.name,
          canonicalName,
          companyType: company.typeHint ?? 'company',
        });
        result.companiesCreated++;
        companyIds.set(canonicalName, id);
      }
    }

    const personIds = new Map<string, string>();
    for (const person of params.mentions.people) {
      const canonicalName = person.name.toLowerCase();
      const existing = this.entityRepo.findByCanonicalName('person', canonicalName);
      if (existing) {
        result.peopleMatched++;
        personIds.set(canonicalName, existing.id);
      } else {
        const id = this.entityRepo.upsert({
          sourceId: params.sourceId,
          entityType: 'person',
          name: person.name,
          canonicalName,
          position: person.roleHint ?? undefined,
        });
        result.peopleCreated++;
        personIds.set(canonicalName, id);
      }
    }

    for (const person of params.mentions.people) {
      const personId = personIds.get(person.name.toLowerCase())!;
      for (const rel of person.relatedTo) {
        const targetCanonicalName = rel.name.toLowerCase();
        if (rel.type === 'title') {
          const titleId = titleIds.get(targetCanonicalName);
          if (!titleId) continue;
          const isCast = rel.relationship === 'actor';
          this.creditRepo.upsert({
            personId,
            titleId,
            sourceId: params.sourceId,
            // Mirrors the TMDB convention: role holds the character name for
            // cast credits, the job title for crew credits.
            role: isCast ? (rel.character ?? 'actor') : rel.relationship,
            creditCategory: isCast ? 'cast' : 'crew',
            trustState: LLM_TRUST_STATE,
          });
          result.creditsCreated++;
        } else if (rel.type === 'company') {
          const companyId = companyIds.get(targetCanonicalName);
          if (!companyId) continue;
          this.companyRelationRepo.upsert({
            companyAId: companyId,
            entityType: 'person',
            entityId: personId,
            relationship: rel.relationship,
            sourceId: params.sourceId,
            trustState: LLM_TRUST_STATE,
          });
          result.companyRelationsCreated++;
        }
        // type === "person": no structured record, just the mention link below.
      }
    }

    const allEntityIds = [...personIds.values(), ...titleIds.values(), ...companyIds.values()];
    for (const entityId of allEntityIds) {
      this.articleRepo.linkEntity({
        articleEntityId: makeStableId('article_entity', params.articleId, entityId, 'mentioned'),
        articleId: params.articleId,
        entityId,
        sourceId: params.sourceId,
        relation: 'mentioned',
      });
      result.mentionsRecorded++;
    }

    this.extractionRepo.save({
      id: makeStableId('extraction', params.rawRecordId, SCHEMA_VERSION_V2),
      documentId: params.rawRecordId,
      jobId: params.jobId ?? null,
      schemaVersion: SCHEMA_VERSION_V2,
      promptVersion: params.promptVersion,
      modelName: params.modelName,
      status: 'succeeded',
      rawJson: params.rawJson,
      resultJson: JSON.stringify(params.mentions),
    });

    return result;
  }

  /** Fetches unprocessed article content, runs LLM extraction, and materializes results. */
  async enrichNext(options: EnrichNextOptions): Promise<EnrichNextSummary> {
    const promptVersion = options.promptVersion ?? PROMPT_VERSION_V2;
    const pending = this.articleRepo.findUnextractedContent(SCHEMA_VERSION_V2, options.limit);

    const totals: EnrichNextSummary = {
      articlesProcessed: 0,
      articlesFailed: 0,
      peopleCreated: 0,
      peopleMatched: 0,
      titlesCreated: 0,
      titlesMatched: 0,
      companiesCreated: 0,
      companiesMatched: 0,
      creditsCreated: 0,
      companyRelationsCreated: 0,
      mentionsRecorded: 0,
    };

    for (const item of pending) {
      const article = this.articleRepo.findArticleById(item.articleId);
      if (!article) continue;

      let response: Awaited<ReturnType<LlmCall>>;
      try {
        response = await this.llmCall(item.text, promptVersion, options.model, options.provider);
      } catch (e) {
        // One bad LLM response (malformed JSON, empty content, timeout)
        // shouldn't abort the rest of the batch.
        console.error(`article enrichment failed for ${item.articleId}: ${(e as Error).message}`);
        totals.articlesFailed++;
        continue;
      }

      const result = this.materializeMentions({
        articleId: item.articleId,
        rawRecordId: item.rawRecordId,
        mentions: response.mentions,
        sourceId: article.sourceId,
        promptVersion,
        modelName: response.modelName,
        rawJson: response.rawJson,
      });

      totals.articlesProcessed++;
      totals.peopleCreated += result.peopleCreated;
      totals.peopleMatched += result.peopleMatched;
      totals.titlesCreated += result.titlesCreated;
      totals.titlesMatched += result.titlesMatched;
      totals.companiesCreated += result.companiesCreated;
      totals.companiesMatched += result.companiesMatched;
      totals.creditsCreated += result.creditsCreated;
      totals.companyRelationsCreated += result.companyRelationsCreated;
      totals.mentionsRecorded += result.mentionsRecorded;
    }

    return totals;
  }
}
