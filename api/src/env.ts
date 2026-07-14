import { homedir } from 'node:os';
import { resolve } from 'node:path';

import { z } from 'zod';

const REPO_ROOT = resolve(import.meta.dirname, '../../');

// Load repo-root .env once so HOLLYWOOD_*/TMDB_API_KEY/OPENROUTER_API_KEY are
// available even when the API isn't started with --env-file.
try {
  process.loadEnvFile(resolve(REPO_ROOT, '.env'));
} catch {
  // .env is optional; real deployments set env vars directly.
}

function expandAndResolve(value: string): string {
  const expanded = value.startsWith('~') ? value.replace('~', homedir()) : value;
  return resolve(REPO_ROOT, expanded);
}

const EnvSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65535).default(4000),
  HOST: z.string().default('0.0.0.0'),
  HOLLYWOOD_DATA_DIR: z.string().default('data').transform(expandAndResolve),
  HOLLYWOOD_DB_PATH: z.string().default('~/.hominem/hollywood.db').transform(expandAndResolve),
  HOLLYWOOD_LOG_LEVEL: z.string().default('INFO'),
  HOLLYWOOD_USER_AGENT: z.string().default('ResearchBot/0.2 contact@example.com'),
  HOLLYWOOD_REQUEST_TIMEOUT_SECONDS: z.coerce.number().int().min(5).max(300).default(30),
  TMDB_API_KEY: z.string().min(1).optional(),
  OPENROUTER_API_KEY: z.string().min(1).optional(),
  OPENAI_API_KEY: z.string().min(1).optional(),
  OLLAMA_BASE_URL: z.string().default('http://localhost:11434/v1'),
});

function loadEnv(): z.infer<typeof EnvSchema> {
  const result = EnvSchema.safeParse(process.env);
  if (!result.success) {
    console.error('Invalid environment configuration:');
    for (const issue of result.error.issues) {
      console.error(`  ${issue.path.join('.')}: ${issue.message}`);
    }
    throw new Error('Invalid environment configuration — see errors above.');
  }
  return result.data;
}

export const env = loadEnv();

export const PORT = env.PORT;
export const HOST = env.HOST;
