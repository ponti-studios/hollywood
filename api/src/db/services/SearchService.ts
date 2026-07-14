import { z } from '@hono/zod-openapi';
import { CreditRepository } from '../repositories/CreditRepository.js';
import { EntityRepository } from '../repositories/EntityRepository.js';

// ── API schemas (source of truth for both the OpenAPI route and this service) ─

export const SearchCreditSchema = z.object({
  id: z.string(),
  role: z.string(),
  type: z.string().nullable(),
  production: z.string(),
  network: z.string().nullable(),
});

export const SearchResultSchema = z.object({
  id: z.string(),
  name: z.string(),
  agencyBio: z.string().nullable(),
  position: z.string(),
  status: z.string(),
  credits: z.array(SearchCreditSchema),
});

export const SearchResultsSchema = z.object({
  total: z.number().int(),
  entities: z.array(SearchResultSchema),
});

export type SearchResult = z.infer<typeof SearchResultSchema>;
export type SearchResults = z.infer<typeof SearchResultsSchema>;

export class SearchService {
  private entityRepo: EntityRepository;
  private creditRepo: CreditRepository;

  constructor(opts?: { entityRepo?: EntityRepository; creditRepo?: CreditRepository }) {
    this.entityRepo = opts?.entityRepo ?? new EntityRepository();
    this.creditRepo = opts?.creditRepo ?? new CreditRepository();
  }

  search(query: string, limit = 20, offset = 0): SearchResults {
    const { rows, total } = this.entityRepo.searchByName(query, limit, offset);
    const entities = rows.map((row) => ({
      id: row.id,
      name: row.name,
      agencyBio: row.bio ?? null,
      position: row.position ?? '',
      status: row.status ?? 'active',
      credits: this.creditRepo.findByPerson(row.id).map((c) => ({
        id: c.id,
        role: c.role,
        type: c.creditCategory ?? null,
        production: c.titleName ?? 'Unknown',
        network: null,
      })),
    }));
    return { total, entities };
  }
}
