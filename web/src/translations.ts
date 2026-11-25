import chinese from './zh-CN.json';
export type Language = 'en' | 'zh-CN';
const catalog: Record<string, string> = chinese;
const templates = Object.entries(catalog).filter(([key]) => /\{\d+\}/.test(key)).map(([key, value]) => ({
  pattern: new RegExp(`^${key.split(/\{\d+\}/).map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('(.+?)')}$`), value,
}));
export function translate(text: string | undefined, language: Language): string {
  if (text == null) return '';
  if (language === 'en') return text;
  const trimmed = text.trim();
  const exact = catalog[trimmed];
  if (exact) return text.replace(trimmed, exact);
  for (const { pattern, value } of templates) {
    const match = trimmed.match(pattern);
    if (match) return value.replace(/\{(\d+)\}/g, (_, index) => translate(match[Number(index) + 1], language));
  }
  return text;
}
