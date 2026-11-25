import { useSyncExternalStore } from 'react';
import { translate, type Language } from './translations';
const listeners = new Set<() => void>();
let language: Language = 'en';
try { if ((localStorage.getItem('capitol-language') ?? document.cookie.match(/(?:^|;\s*)capitol-language=([^;]+)/)?.[1]) === 'zh-CN') language = 'zh-CN'; } catch { /* Private browsing can disable storage. */ }
export const getLanguage = () => language;
export const locale = () => language === 'zh-CN' ? 'zh-CN' : 'en-US';
export const t = (text: string | undefined) => translate(text, language);
export function setLanguage(value: Language) {
  language = value;
  try { localStorage.setItem('capitol-language', value); } catch { /* In-memory preference still works. */ }
  document.documentElement.lang = value;
  document.cookie = `capitol-language=${value}; Path=/capitol-lens; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
  for (const listener of listeners) listener();
}
export function useLanguage() {
  return useSyncExternalStore(listener => { listeners.add(listener); return () => { listeners.delete(listener); }; }, getLanguage, () => 'en' as Language);
}
