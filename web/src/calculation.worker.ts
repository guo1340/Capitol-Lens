import { simulate } from './simulate';
import type { Dataset, SimulationSettings } from './types';
self.onmessage = (event: MessageEvent<{ data: Dataset; settings: SimulationSettings }>) => {
  try { self.postMessage({ result: simulate(event.data.data, event.data.settings) }); }
  catch (error) { self.postMessage({ error: error instanceof Error ? error.message : 'Calculation failed.' }); }
};
