import { useEffect, useRef, useState } from 'react';
import { MessageCircle, Send, X } from 'lucide-react';
import { Help } from './Help';
import { glossary, type GlossaryKey } from './glossary';
import type { Dataset, SimulationSettings } from './types';

interface Source { id: string; label: string; ticker?: string; url?: string }
interface Message { role: 'user' | 'assistant'; content: string; sources?: Source[]; model?: string }
const starters = ['Give me the simple version of this data.', 'Which three stocks deserve a closer look based on this history, and why?', 'What could go wrong if I copy these trades?', 'Explain my what-if result in everyday language.'];
const terms = Object.entries(glossary).map(([key, entry]) => ({ key: key as GlossaryKey, title: entry.title })).sort((a, b) => b.title.length - a.title.length);
const termPattern = new RegExp(`\\b(${terms.map(t => t.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'gi');
function ExplainedText({ text }: { text: string }) {
  return <>{text.split(termPattern).map((part, i) => {
    const term = terms.find(t => t.title.toLowerCase() === part.toLowerCase());
    return term ? <span key={i}>{part}<Help term={term.key}/></span> : part;
  })}</>;
}

export function Chat({ data, configured, settings, stock, viewStock }: { data: Dataset; configured: boolean; settings: SimulationSettings; stock: string; viewStock: (ticker: string) => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [includeScenario, setIncludeScenario] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { if (messages.length) bottom.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [messages, busy]);
  async function send(question = draft) {
    if (!question.trim() || busy || !configured) return;
    const next: Message[] = [...messages, { role: 'user', content: question.trim() }];
    setMessages(next); setDraft(''); setError(''); setBusy(true);
    const abort = new AbortController(); controller.current = abort;
    try {
      const response = await fetch('/capitol-lens/api/chat', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, signal: abort.signal,
        body: JSON.stringify({ messages: next.slice(-9).map(m => ({ role: m.role, content: m.content.slice(0, 6000) })), selectedStock: stock, ...(includeScenario ? { scenario: settings } : {}) }) });
      const result = await response.json() as { message?: string; answer: string; sources: Source[]; model: string };
      if (!response.ok) throw new Error(result.message ?? 'Chat could not verify access or complete this request. Please retry.');
      if (!abort.signal.aborted) setMessages([...next, { role: 'assistant', content: result.answer, sources: result.sources, model: result.model }]);
    } catch (e) {
      if (!abort.signal.aborted) { setError((e as Error).message); setDraft(question); setMessages(messages); }
    } finally { if (controller.current === abort) { setBusy(false); controller.current = null; } }
  }
  function cancel() { controller.current?.abort(); controller.current = null; setBusy(false); }
  return <section className="panel chat-panel" aria-label="Chat with AI">
    <div className="panel-heading"><div><span className="eyebrow">MAKE SENSE OF THE NUMBERS</span><h2><MessageCircle size={20}/> Your research companion <Help term="aiResearch"/></h2></div><button className="secondary" onClick={() => { cancel(); setMessages([]); setError(''); setDraft(''); }}>New chat</button></div>
    <div className="chat-context"><span>Using data from <strong>{data.coverageStart} to {data.coverageEnd}</strong><Help term="snapshot"/></span><span>No live news or latest quotes in chat<Help term="coverage"/></span></div>
    {!configured && <div className="notice" role="status">Chat is not connected yet. Add OPENAI_API_KEY to your backend’s .dev.vars file, then restart the backend. For hosting, use a Worker secret. See the README for setup.<Help term="apiAccess"/></div>}
    <div className="chat-log" role="log" aria-label="Conversation" aria-live="polite">
      {!messages.length && <div className="chat-welcome"><span className="empty-illustration"><MessageCircle size={32}/></span><h2>Start with a simple question.</h2><p>Ask what stands out, compare a few stocks, or get help understanding your what-if. Buying ideas will be based on the dated history above.</p><div className="chat-starters">{starters.map(prompt => <button className="secondary" disabled={busy} key={prompt} onClick={() => { setDraft(prompt); if (prompt.includes('what-if')) setIncludeScenario(true); }}>{prompt}</button>)}</div></div>}
      {messages.map((m, i) => <article key={i} className={`chat-message ${m.role}`}><strong>{m.role === 'user' ? 'You' : 'Capitol Lens AI'}</strong><div className="chat-answer">{m.role === 'assistant' ? <ExplainedText text={m.content}/> : m.content}</div>{m.sources && m.sources.length > 0 && <div className="chat-sources" aria-label="Supporting records">{m.sources.map(s => s.url && /^https:\/\/disclosures-clerk\.house\.gov\//.test(s.url) ? <a key={s.id} href={s.url} target="_blank" rel="noreferrer">[{s.id}] {s.label}</a> : s.ticker ? <button key={s.id} className="text-button" onClick={() => viewStock(s.ticker!)}>[{s.id}] {s.label}</button> : <span key={s.id}>[{s.id}] {s.label}</span>)}</div>}{m.model && <small className="subtle">{m.model} · Check the supporting records <Help term="aiResearch"/></small>}</article>)}
      {busy && <p className="chat-thinking" role="status">Reading the historical evidence… <button className="text-button" onClick={cancel}>Stop</button></p>}
      <div ref={bottom}/>
    </div>
    {error && <div className="notice error" role="alert">{error}<button className="icon-button" aria-label="Dismiss chat error" onClick={() => setError('')}><X size={16}/></button></div>}
    <form className="chat-compose" onSubmit={e => { e.preventDefault(); void send(); }}>
      <label className="chat-scenario"><input type="checkbox" checked={includeScenario} onChange={e => setIncludeScenario(e.target.checked)}/>Include my current what-if settings<Help term="backtest"/></label>
      {includeScenario && <small>Recalculates your settings for this answer: {settings.politicians.join(', ') || 'no politicians selected'} · {settings.start} to {settings.end} · ${settings.initial.toLocaleString()}.</small>}
      <label htmlFor="chat-question">Your question</label><textarea id="chat-question" value={draft} maxLength={2000} rows={3} onChange={e => setDraft(e.target.value)} placeholder="What does this mean for someone just getting started?"/>
      <div className="chat-send-row"><span>{draft.length}/2,000 · Messages are sent to OpenAI<Help term="chatPrivacy"/></span><button className="primary" type="submit" disabled={!configured || busy || !draft.trim()}><Send size={16}/>{busy ? 'Thinking…' : 'Send question'}</button></div>
    </form>
  </section>;
}
