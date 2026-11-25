import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { describe, it, expect } from 'vitest';
import { simulate } from '../src/simulate';
import type { Dataset, SimulationSettings, SimulationResult } from '../src/types';
import references from './expected-backtests.json';

// Frozen original research input: daily refreshes must not rewrite the oracle.
const data: Dataset = JSON.parse(gunzipSync(readFileSync(new URL('./historical-fixture.json.gz', import.meta.url))).toString());
describe('independent Python research parity', () => {
  for (const [index, reference] of references.entries()) {
    it(`matches Python scenario ${index + 1}: ${reference.settings.politicians.join(', ')} ${reference.settings.start}`, () => {
      const result = simulate(data, reference.settings as SimulationSettings);
      for (const [key, value] of Object.entries(reference.expected)) expect(result[key as keyof SimulationResult]).toBeCloseTo(value, 6);
      expect(result.orders).toHaveLength(reference.orders);
      expect(result.curve.every(p => p.cash >= -1e-6)).toBe(true);
    });
  }
});
it('rejects incomplete extraction and out-of-coverage scenarios', () => {
  const settings = references[0].settings as SimulationSettings;
  expect(() => simulate({ ...data, sourceIssues: 1 }, settings)).toThrow('source reports');
  expect(() => simulate(data, { ...settings, end: '2030-01-01' })).toThrow('valid dates');
  expect(() => simulate(data, { ...settings, initial: NaN })).toThrow('valid dates');
});
