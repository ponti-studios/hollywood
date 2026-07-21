import { serve } from '@hono/node-server';
import { OpenAPIHono } from '@hono/zod-openapi';

import { closeDb } from './db.js';
import { HOST, PORT, env } from './env.js';
import { registerAllAdapters } from './ingestion/adapters/index.js';
import articleEnrichmentRouter from './routes/article_enrichment.js';
import candidatesRouter from './routes/candidates.js';
import doctorRouter from './routes/doctor.js';
import exportRouter from './routes/export.js';
import ingestRouter from './routes/ingest.js';
import ingestSourceRouter from './routes/ingest_source.js';
import normalizeRouter from './routes/normalize.js';
import projectsRouter from './routes/projects.js';
import searchRouter from './routes/search.js';
import sourcesRouter from './routes/sources.js';
import submissionsRouter from './routes/submissions.js';
import tagsRouter from './routes/tags.js';

registerAllAdapters();

const DB_PATH = env.HOLLYWOOD_DB_PATH;

// ── App ─────────────────────────────────────────────────────────────────────

const app = new OpenAPIHono();

// OpenAPI documentation
app.doc('/openapi', {
  openapi: '3.0.0',
  info: {
    title: 'backlot',
    version: '0.1.0',
    description: 'Entertainment graph API — unified entity database for TV/film industry',
  },
  servers: [{ url: `http://${HOST}:${PORT}`, description: 'Local development' }],
});

// Health check
app.get('/', (c) => c.json({ status: 'ok', db: DB_PATH }, 200));
app.get('/health', (c) => c.json({ status: 'ok' }, 200));

// Mount route modules
app.route('/', candidatesRouter);
app.route('/', projectsRouter);
app.route('/', submissionsRouter);
app.route('/', searchRouter);
app.route('/', tagsRouter);
app.route('/', ingestRouter);
app.route('/', ingestSourceRouter);
app.route('/', sourcesRouter);
app.route('/', normalizeRouter);
app.route('/', exportRouter);
app.route('/', doctorRouter);
app.route('/', articleEnrichmentRouter);

// ── Server ──────────────────────────────────────────────────────────────────

const server = serve({ fetch: app.fetch, port: PORT, hostname: HOST }, (info) => {
  console.log(`🎬 backlot running at http://${HOST}:${info.port}`);
  console.log(`   Database: ${DB_PATH}`);
  console.log(`   OpenAPI:  http://${HOST}:${info.port}/openapi`);
});

process.on('SIGINT', () => {
  console.log('\nShutting down...');
  closeDb();
  server.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  closeDb();
  server.close();
  process.exit(0);
});
