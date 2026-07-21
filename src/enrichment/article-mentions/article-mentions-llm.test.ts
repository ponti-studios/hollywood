import { describe, expect, it } from 'vitest';

import { stripCodeFence } from './article-mentions-llm.js';

describe('stripCodeFence', () => {
  it('passes through plain JSON unchanged', () => {
    expect(stripCodeFence('{"a":1}')).toBe('{"a":1}');
  });

  it('strips a ```json fenced block', () => {
    expect(stripCodeFence('```json\n{"a":1}\n```')).toBe('{"a":1}');
  });

  it('strips a bare ``` fenced block', () => {
    expect(stripCodeFence('```\n{"a":1}\n```')).toBe('{"a":1}');
  });

  it('trims surrounding whitespace', () => {
    expect(stripCodeFence('  {"a":1}  \n')).toBe('{"a":1}');
  });
});
