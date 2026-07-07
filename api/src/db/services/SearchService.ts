import { EntityRepository } from "../repositories/EntityRepository.js";
import { CreditRepository } from "../repositories/CreditRepository.js";

export interface SearchResult {
  id: string;
  name: string;
  agencyBio: string | null;
  position: string;
  status: string;
  credits: Array<{
    id: string;
    role: string;
    type: string | null;
    production: string;
    network: string | null;
  }>;
}

export interface SearchResults {
  total: number;
  entities: SearchResult[];
}

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
      position: row.position ?? "",
      status: row.status ?? "active",
      credits: this.creditRepo.findByPerson(row.id).map((c) => ({
        id: c.id,
        role: c.role,
        type: c.creditType ?? null,
        production: c.titleName ?? "Unknown",
        network: null,
      })),
    }));
    return { total, entities };
  }
}
