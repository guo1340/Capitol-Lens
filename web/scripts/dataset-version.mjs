import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const data=readFileSync(new URL('../public/data/dataset.json',import.meta.url));
writeFileSync(new URL('../public/data/dataset-version.json',import.meta.url),JSON.stringify({version:createHash('sha256').update(data).digest('hex')}));
