import { registerAdapter } from '../flows.js';
import { getSource } from '../registry.js';
import { RssAdapter } from './rss.js';
import { TmdbAdapter } from './tmdb.js';
import { WgaAdapter } from './wga.js';
import { WikidataAdapter } from './wikidata.js';

/** Import this module once (e.g. from api/src/index.ts) to register all ported adapters. */
export function registerAllAdapters(): void {
  for (const sourceId of ['variety', 'deadline', 'hollywood_reporter', 'the_wrap']) {
    registerAdapter(sourceId, new RssAdapter(getSource(sourceId)));
  }
  registerAdapter('tmdb', new TmdbAdapter(getSource('tmdb')));
  registerAdapter('wikidata', new WikidataAdapter(getSource('wikidata')));
  registerAdapter('wga', new WgaAdapter(getSource('wga')));
}
