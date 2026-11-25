import { t, useLanguage } from './i18n';
import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { glossary, type GlossaryKey } from './glossary';

export function Help({ term }: { term: GlossaryKey }) {
  useLanguage();
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [position, setPosition] = useState<{ left: number; top: number; above: boolean } | null>(null);
  const entry = glossary[term];
  function open() {
    if (timer.current) clearTimeout(timer.current);
    const box = button.current!.getBoundingClientRect();
    setPosition({ left: Math.max(12, Math.min(box.left - 120, window.innerWidth - 332)), top: box.bottom + 10, above: box.bottom > window.innerHeight - 190 });
  }
  function closeSoon() { timer.current = setTimeout(() => setPosition(null), 140); }
  useEffect(() => {
    const close = (e: KeyboardEvent) => { if (e.key === 'Escape') setPosition(null); };
    const scroll = () => setPosition(null);
    window.addEventListener('keydown', close); window.addEventListener('scroll', scroll, true);
    return () => { window.removeEventListener('keydown', close); window.removeEventListener('scroll', scroll, true); if (timer.current) clearTimeout(timer.current); };
  }, []);
  return <><button ref={button} type="button" className="help" aria-label={t(`Explain ${t(entry.title)}`)} aria-describedby={position ? id : undefined}
    onMouseEnter={open} onMouseLeave={closeSoon} onFocus={open} onBlur={closeSoon} onClick={open}>?</button>
    {position && createPortal(<div id={id} role="tooltip" className="dictionary-tooltip" style={{ left: position.left, top: position.above ? position.top - 22 : position.top, transform: position.above ? 'translateY(-100%)' : undefined }}
      onMouseEnter={() => { if (timer.current) clearTimeout(timer.current); }} onMouseLeave={closeSoon}><strong>{t(entry.title)}</strong><p>{t(entry.text)}</p></div>, button.current?.closest('dialog') ?? document.body)}</>;
}
