import { t as tr, useLanguage, setLanguage, locale } from './i18n';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BookOpen, ChevronRight, Compass, ExternalLink, FlaskConical, Layers3, MessageCircle, Moon, RefreshCw, Search, ShieldCheck, Sun, X } from 'lucide-react';
import { Help } from './Help';
import { Chat } from './Chat';
import { Manual } from './Manual';
import { glossary, type GlossaryKey } from './glossary';
import type { Dataset, SimulationResult, SimulationSettings, Trade } from './types';
const API = '/capitol-lens/api';
const money = (n: number | undefined | null, digits = 2) => n == null ? tr('Unavailable') : n.toLocaleString(locale(), { style: 'currency', currency: 'USD', maximumFractionDigits: digits });
const percent = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
const shortDate = (d: string) => new Date(`${d.slice(0, 10)}T12:00:00Z`).toLocaleDateString(locale(), { month: 'short', day: 'numeric', year: 'numeric' });
const lag = (t: Trade) => Math.round((Date.parse(t.filingDate) - Date.parse(t.tradeDate)) / 86400000);
const colors = ['#7cb9d9', '#e1a36c', '#bd9bdd', '#7dc5b1', '#d58ba2', '#adbf72'];
type Tab = 'explore' | 'stock' | 'whatif' | 'chat' | 'manual';
interface Status {
    chatConfigured: boolean;
    quoteConfigured: boolean;
    refreshConfigured: boolean;
    repository: string | null;
    environment: string;
}
interface Quote {
    price: number;
    asOf: string;
    provider: string;
    changePercent: number | null;
}
async function api<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API}${path}`, { ...options, credentials: 'same-origin' });
    if (response.status === 401 || response.status === 403)
        throw new Error('Access could not be verified. Sign in at admin.guopq.com, then return here and retry. For local development, start npm run dev:backend in a separate terminal.');
    const body = await response.json() as {
        message?: string;
        error?: string;
    };
    if (!response.ok)
        throw new Error(body.message ?? body.error ?? tr('The request failed.'));
    return body as T;
}
function Metric({ label, term, value, detail, tone }: {
    label: string;
    term: GlossaryKey;
    value: string;
    detail?: string;
    tone?: string;
}) {
    return <div className="metric"><span className="metric-label">{label}<Help term={term}/></span><strong className={tone}>{value}</strong>{detail && <small>{detail}</small>}</div>;
}
export default function App() {
    const language = useLanguage();
    useEffect(() => { document.documentElement.lang = language; }, [language]);
    const [theme, setTheme] = useState(() => localStorage.getItem('capitol-theme') ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
    const [data, setData] = useState<Dataset | null>(null);
    const [status, setStatus] = useState<Status | null>(null);
    const [error, setError] = useState('');
    const [tab, updateTab] = useState<Tab>(() => location.pathname.replace(/\/$/, '') === '/capitol-lens/manual' ? 'manual' : 'explore');
    function setTab(next: Tab) {
        const path = next === 'manual' ? '/capitol-lens/manual' : '/capitol-lens/';
        if (location.pathname !== path) { window.history.replaceState({ tab }, '', location.href); window.history.pushState({ tab: next }, '', path); }
        updateTab(next);
        window.scrollTo({ top: 0 });
    }
    useEffect(() => {
        const onPop = (event: PopStateEvent) => updateTab(location.pathname.replace(/\/$/, '') === '/capitol-lens/manual' ? 'manual' : event.state?.tab ?? 'explore');
        window.addEventListener('popstate', onPop);
        return () => window.removeEventListener('popstate', onPop);
    }, []);
    const [person, setPerson] = useState('all');
    const [search, setSearch] = useState('');
    const [direction, setDirection] = useState('all');
    const [year, setYear] = useState('all');
    const [limit, setLimit] = useState(15);
    const [stock, setStock] = useState('NVDA');
    const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
    const [quote, setQuote] = useState<Quote | null>(null);
    const [quoteError, setQuoteError] = useState('');
    const [quoting, setQuoting] = useState(false);
    const [refreshMessage, setRefreshMessage] = useState('');
    const [refreshing, setRefreshing] = useState(false);
    const [dictionary, setDictionary] = useState(false);
    const [dictionarySearch, setDictionarySearch] = useState('');
    const [settings, setSettings] = useState<SimulationSettings>({ politicians: [], start: '2024-01-01', end: '2025-12-31', initial: 10000, buyFraction: .05, capFraction: .2, sizing: 'initial', costPercent: .1, partialFraction: .5, extraDays: 0 });
    const [result, setResult] = useState<SimulationResult | null>(null);
    const [runError, setRunError] = useState('');
    const [running, setRunning] = useState(false);
    const [dirty, setDirty] = useState(false);
    const calculation = useRef<Worker | null>(null);
    const currentStock = useRef(stock);
    currentStock.current = stock;
    const dictionaryRef = useRef<HTMLDialogElement>(null);
    useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('capitol-theme', theme); }, [theme]);
    useEffect(() => {
        let active = true;
        Promise.all([api<Dataset>('/dataset'), api<Status>('/status')]).then(([dataset, state]) => {
            if (!active)
                return;
            setData(dataset);
            setStatus(state);
            setSettings(s => ({ ...s, politicians: dataset.politicians.map(p => p.id), start: dataset.coverageStart, end: dataset.coverageEnd }));
        }).catch(e => active && setError(e.message));
        return () => { active = false; calculation.current?.terminate(); };
    }, []);
    useEffect(() => { if (dictionary)
        dictionaryRef.current?.showModal();
    else
        dictionaryRef.current?.close(); }, [dictionary]);
    useEffect(() => { setLimit(15); }, [person, search, direction, year]);
    useEffect(() => { setQuote(null); setQuoteError(''); }, [stock]);
    const included = useMemo(() => data?.trades.filter(t => !t.excludedReason) ?? [], [data]);
    const years = useMemo(() => [...new Set(included.map(t => t.filingDate.slice(0, 4)))].sort(), [included]);
    const filtered = useMemo(() => included.filter(t => (person === 'all' || t.politician === person) &&
        (direction === 'all' || t.action === direction) && (year === 'all' || t.filingDate.startsWith(year)) &&
        `${t.ticker} ${data?.companies[t.ticker ?? ''] ?? ''} ${t.politician} ${data?.politicians.find(p => p.id === t.politician)?.name ?? ''}`.toLowerCase().includes(search.toLowerCase()))
        .sort((a, b) => b.filingDate.localeCompare(a.filingDate) || b.tradeDate.localeCompare(a.tradeDate)), [included, person, direction, year, search, data, language]);
    const popular = useMemo(() => {
        const counts: Record<string, number> = {};
        for (const t of filtered)
            if (t.ticker)
                counts[t.ticker] = (counts[t.ticker] ?? 0) + 1;
        return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
    }, [filtered]);
    const history = data?.prices[stock] ?? [];
    const stockTrades = included.filter(t => t.ticker === stock && (person === 'all' || t.politician === person)).sort((a, b) => b.filingDate.localeCompare(a.filingDate));
    const activeTrade = selectedTrade?.ticker === stock && stockTrades.some(t => t.id === selectedTrade.id) ? selectedTrade : stockTrades[0];
    const tradePrice = history.find(p => p.date === activeTrade?.tradeDate);
    const disclosedPrice = history.find(p => p.date > (activeTrade?.filingDate ?? '9999'));
    const last = history.at(-1);
    const chartData = history;
    const uniqueStocks = new Set(filtered.map(t => t.ticker)).size;
    const sortedLags = filtered.map(lag).sort((a, b) => a - b);
    const middle = Math.floor(sortedLags.length / 2);
    const medianLag = sortedLags.length ? (sortedLags.length % 2 ? sortedLags[middle] : (sortedLags[middle - 1] + sortedLags[middle]) / 2) : 0;
    function viewStock(ticker: string, trade?: Trade) { setStock(ticker); setSelectedTrade(trade ?? null); setTab('stock'); window.scrollTo({ top: 0, behavior: 'smooth' }); }
    function updateSettings(patch: Partial<SimulationSettings>) { setSettings(s => ({ ...s, ...patch })); setDirty(true); }
    function run() {
        if (!data)
            return;
        setRunning(true);
        setRunError('');
        calculation.current?.terminate();
        const worker = new Worker(new URL('./calculation.worker.ts', import.meta.url), { type: 'module' });
        calculation.current = worker;
        worker.onmessage = event => { setRunning(false); if (event.data.error) {
            setRunError(event.data.error);
            setResult(null);
        }
        else {
            setResult(event.data.result);
            setDirty(false);
        } worker.terminate(); };
        worker.onerror = () => { setRunning(false); setRunError('The calculation could not finish. Please retry.'); worker.terminate(); };
        worker.postMessage({ data, settings });
    }
    async function fetchQuote() {
        const requested = stock;
        setQuoting(true);
        setQuoteError('');
        try {
            const q = await api<Quote>(`/quote?symbol=${encodeURIComponent(stock)}`);
            if (requested === currentStock.current)
                setQuote(q);
        }
        catch (e) {
            if (requested === currentStock.current)
                setQuoteError((e as Error).message);
        }
        finally {
            setQuoting(false);
        }
    }
    async function refresh() {
        setRefreshing(true);
        setRefreshMessage('');
        try {
            const r = await api<{
                message: string;
            }>('/refresh', { method: 'POST' });
            setRefreshMessage(r.message);
        }
        catch (e) {
            setRefreshMessage((e as Error).message);
        }
        finally {
            setRefreshing(false);
        }
    }
    if (!data)
        return <main className="loading-page"><div className="brand-symbol"><Layers3 /></div><h1>Capitol Lens</h1><button className="language-button" onClick={() => setLanguage(language === 'en' ? 'zh-CN' : 'en')}>{language === 'en' ? '中文' : 'English'}</button><p>{tr(error) || tr('Opening your research workspace…')}</p>{error && <button className="primary" onClick={() => location.reload()}>{tr("Try again")}</button>}</main>;
    return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="/capitol-lens/"><span className="brand-symbol"><Layers3 size={23}/></span><span>Capitol Lens<small>{tr("FOLLOW THE DISCLOSURES")}</small></span></a>
      <div className="nav-caption">{tr("RESEARCH WORKSPACE")}</div><nav aria-label={tr("Main navigation")}>
        <button className={tab === 'explore' ? 'active' : ''} onClick={() => setTab('explore')}><Compass size={20}/>{tr("Explore trades")}</button>
        <button className={tab === 'stock' ? 'active' : ''} onClick={() => setTab('stock')}><Layers3 size={20}/>{tr("Stock story")}</button>
        <button className={tab === 'whatif' ? 'active' : ''} onClick={() => setTab('whatif')}><FlaskConical size={20}/>{tr("What if")}</button>
      <button className={tab === 'chat' ? 'active' : ''} onClick={() => setTab('chat')}><MessageCircle size={20}/>{tr("Chat with AI")}</button><button className={tab === 'manual' ? 'active' : ''} onClick={() => setTab('manual')}><BookOpen size={20}/>{tr('User manual')}</button></nav><div className="sidebar-note"><span className="eyebrow">{tr("YOUR STARTING POINT")}</span><strong>{tr("Follow the evidence.")}<br />{tr("Explore the possibilities.")}</strong><p>{tr("Six politicians. Public reports. A clearer view of the stocks behind them.")}</p></div>
      <div className="sidebar-bottom"><button className="quiet" onClick={() => setDictionary(true)}><BookOpen size={18}/>{tr("Word help")}</button><div className="private-label"><ShieldCheck size={17}/><span>{tr("Private workspace")}<small>guo1340@vt.edu</small></span></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">{tr("Workspace")}<ChevronRight size={14}/><strong>{tab === 'manual' ? tr('User manual') : tab === 'explore' ? tr('Explore trades') : tab === 'stock' ? tr('Stock story') : tab === 'chat' ? tr('Chat with AI') : tr('What if')}</strong></div><div className="top-actions"><button className="language-button" aria-label={language === 'en' ? '切换到中文' : 'Switch to English'} onClick={() => setLanguage(language === 'en' ? 'zh-CN' : 'en')}>{language === 'en' ? '中文' : 'English'}</button><button className="icon-button" aria-label={tr("Open word help")} onClick={() => setDictionary(true)}><BookOpen size={19}/></button><span className="research-pill">{tr("Research only")}</span><button className="icon-button" aria-label={theme === 'dark' ? tr('Switch to light mode') : tr('Switch to dark mode')} onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? <Sun size={19}/> : <Moon size={19}/>}</button><span className="user-avatar">G</span></div></header>
      <main className="main-content">
        {status?.environment === 'local' && <div className="local-banner">{tr("Local preview \u00B7 test identity \u00B7 production access still uses your admin session")}</div>}
        <section className="page-heading"><div><div className="eyebrow">{tr("PUBLIC TRADES, PUT IN PERSPECTIVE")}</div><h1>{tab === 'manual' ? tr('How to use Capitol Lens.') : tab === 'explore' ? tr('See the trades. Find the connections.') : tab === 'stock' ? tr('Every stock has a story.') : tab === 'chat' ? tr('Let’s make this easier to understand.') : tr('What would your money have done?')}</h1><p>{tab === 'manual' ? tr('A step-by-step guide to the data, simulations and AI chat.') : tab === 'explore' ? tr('Explore what was reported, when we learned about it, and which stocks connect these politicians.') : tab === 'stock' ? tr('Follow a stock’s price alongside the trades that became public.') : tab === 'chat' ? tr('Ask a question. Get a plain-language answer grounded in your research data.') : tr('Choose who to follow, set a budget, and explore a past scenario.')}</p></div><button className="secondary refresh-button" onClick={refresh} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''}/>{refreshing ? tr('Requesting…') : tr('Refresh data')}</button></section>
        {refreshMessage && <div className="notice" role="status">{tr(refreshMessage)}{status?.repository && <a target="_blank" rel="noreferrer" href={`https://github.com/${status.repository}/actions/workflows/refresh-data.yml`}>{tr("View update progress ")}<ExternalLink size={13}/></a>}</div>}
        <div className="coverage-strip"><span><span className="status-dot"/>{tr("Historical coverage ")}<Help term="coverage"/></span><strong>{shortDate(data.coverageStart)} – {shortDate(data.coverageEnd)}</strong><span className="coverage-right">{tr("Snapshot built ")}{shortDate(data.builtAt)} <Help term="snapshot"/></span></div>

        {tab === 'explore' && <>
          <div className="filters"><label className="search-field"><Search size={18}/><input aria-label={tr("Search stocks or politicians")} placeholder={tr("Search a stock or politician")} value={search} onChange={e => setSearch(e.target.value)}/></label><select aria-label={tr("Filter politician")} value={person} onChange={e => setPerson(e.target.value)}><option value="all">{tr("All politicians")}</option>{data.politicians.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select><select aria-label={tr("Filter transaction direction")} value={direction} onChange={e => setDirection(e.target.value)}><option value="all">{tr("Buys & sells")}</option><option value="buy">{tr("Buys only")}</option><option value="sell">{tr("Sells only")}</option></select><select aria-label={tr("Filter filing year")} value={year} onChange={e => setYear(e.target.value)}><option value="all">{tr("All years")}</option>{years.map(y => <option key={y}>{y}</option>)}</select></div>
          <div className="metrics"><Metric label={tr("Reported stock trades")} term="disclosure" value={filtered.length.toLocaleString()} detail={tr("Matching your filters")}/><Metric label={tr("Different stocks")} term="stock" value={String(uniqueStocks)} detail={tr("With eligible disclosures")}/><Metric label={tr("Typical reporting delay")} term="disclosureLag" value={tr(`${medianLag} days`)} detail={tr("Median in this selected sample")}/><Metric label={tr("Politicians in view")} term="portfolio" value={String(person === 'all' ? data.politicians.length : 1)} detail={tr("Includes reported household trades")}/></div>
          <section className="panel connections"><div className="panel-heading"><div><span className="eyebrow">{tr("THE BIG PICTURE")}</span><h2>{tr("Who\u2019s trading the same stocks? ")}<Help term="correlation"/></h2></div><span className="subtle">{tr("Most reported in this view")}</span></div><div className="table-scroll"><table className="connection-table"><thead><tr><th>{tr("Stock ")}<Help term="ticker"/></th>{data.politicians.filter(p => person === 'all' || p.id === person).map((p, i) => <th key={p.id}><span className="person-mini" style={{ background: `${colors[i]}22`, color: colors[i] }}>{p.name.split(' ').map(n => n[0]).slice(0, 2).join('')}</span>{p.name}</th>)}</tr></thead><tbody>{popular.map(([ticker]) => <tr key={ticker}><th><button className="stock-link" onClick={() => viewStock(ticker)}>{ticker}</button><small>{data.companies[ticker] ?? ticker}</small></th>{data.politicians.filter(p => person === 'all' || p.id === person).map(p => { const trades = filtered.filter(t => t.ticker === ticker && t.politician === p.id); const buys = trades.filter(t => t.action === 'buy').length; const sells = trades.filter(t => t.action === 'sell').length; return <td key={p.id}>{trades.length ? <button className="heat-cell" onClick={() => { setPerson(p.id); viewStock(ticker); }}><span className="buy-text">{buys}{tr(" buys")}</span><span className="sell-text">{sells}{tr(" sells")}</span></button> : <span className="empty-cell">—</span>}</td>; })}</tr>)}</tbody></table>{!popular.length && <p className="empty">{tr("No stocks match these filters.")}</p>}</div></section>
          <section className="panel"><div className="panel-heading"><div><span className="eyebrow">{tr("THE SOURCE RECORD")}</span><h2>{tr("Reported trades ")}<Help term="disclosure"/></h2></div><span className="subtle">{tr("Newest filing first")}</span></div><div className="table-scroll"><table><thead><tr><th>{tr("Politician")}</th><th>{tr("Stock ")}<Help term="ticker"/></th><th>{tr("Action")}</th><th>{tr("Traded ")}<Help term="tradeDate"/></th><th>{tr("Filed ")}<Help term="filingDate"/></th><th>{tr("Delay ")}<Help term="disclosureLag"/></th><th>{tr("Amount ")}<Help term="amountRange"/></th><th>{tr("Source")}</th></tr></thead><tbody>{filtered.slice(0, limit).map(t => <tr key={t.id}><td>{data.politicians.find(p => p.id === t.politician)?.name}</td><td><button className="stock-link" onClick={() => viewStock(t.ticker!, t)}>{t.ticker}</button></td><td><span className={`trade-badge ${t.action}`}>{t.action === 'buy' ? tr('Buy') : t.partial ? tr('Partial sale') : tr('Sell')}</span>{t.partial && <Help term="partialSale"/>}</td><td>{shortDate(t.tradeDate)}</td><td>{shortDate(t.filingDate)}</td><td>{lag(t)}{tr(" days")}</td><td>{tr(t.amount)}</td><td><a className="source-link" href={t.sourceUrl} target="_blank" rel="noreferrer" aria-label={tr(`Official filing for ${t.ticker} on ${t.filingDate}`)}><ExternalLink size={16}/></a></td></tr>)}</tbody></table>{!filtered.length && <p className="empty">{tr("No trades match these filters. Try another stock or politician.")}</p>}</div>{filtered.length > limit && <div className="table-footer"><span>{tr("Showing ")}{Math.min(limit, filtered.length)}{tr(" of ")}{filtered.length}</span><button className="secondary" onClick={() => setLimit(l => l + 25)}>{tr("Show more trades")}</button></div>}</section>
        </>}

        {tab === 'stock' && <>
          <div className="filters"><label className="field-inline">{tr("Stock ")}<Help term="ticker"/><select aria-label={tr("Choose stock")} value={stock} onChange={e => { setStock(e.target.value); setSelectedTrade(null); }}>{[...new Set(included.map(t => t.ticker!))].sort().map(t => <option value={t} key={t}>{t} · {data.companies[t] ?? tr('Company name unavailable')}</option>)}</select></label><select aria-label={tr("Stock story politician")} value={person} onChange={e => { setPerson(e.target.value); setSelectedTrade(null); }}><option value="all">{tr("All politicians")}</option>{data.politicians.map(p => <option value={p.id} key={p.id}>{p.name}</option>)}</select></div>
          <div className="stock-heading"><div className="stock-emblem">{stock.slice(0, 2)}</div><div><h2>{stock}</h2><p>{data.companies[stock] ?? tr('Company name unavailable')}</p></div><div className="stock-heading-price"><strong>{money(quote?.price ?? last?.close)}</strong><span>{quote ? `Finnhub · ${new Date(quote.asOf).toLocaleString(locale())}` : last ? tr(`Historical close · ${shortDate(last.date)}`) : tr('No price available')}<Help term="latestPrice"/></span></div></div>
          <section className="panel"><div className="panel-heading"><div><h2>{tr("Price & public filings ")}<Help term="rawPrice"/></h2><span className="subtle">{tr("Select a reported trade below to locate its disclosure on the chart.")}</span></div><div className="legend"><span className="buy-text">{tr("\u25CF Buy disclosed")}</span><span className="sell-text">{tr("\u25CF Sale disclosed")}</span></div></div><div className="chart-container" role="img" aria-label={tr(`${stock} historical price chart with selected disclosure marker`)}>{chartData.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 15, right: 24, bottom: 0, left: 0 }}><defs><linearGradient id="stockFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#64bfa9" stopOpacity={.22}/><stop offset="100%" stopColor="#64bfa9" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="var(--border)"/><XAxis dataKey="date" minTickGap={70} tickFormatter={d => String(d).slice(0, 7)} tick={{ fill: 'var(--muted)', fontSize: 12 }}/><YAxis domain={['auto', 'auto']} tickFormatter={n => `$${n}`} tick={{ fill: 'var(--muted)', fontSize: 12 }} width={65}/><Tooltip contentStyle={{ background: 'var(--panel)', borderColor: 'var(--border)', color: 'var(--text)' }} formatter={v => money(Number(v))}/><Area type="monotone" dataKey="close" name={tr("Historical close")} stroke="#64bfa9" fill="url(#stockFill)" strokeWidth={2} isAnimationActive={false}/>{activeTrade && (() => { const p = chartData.find(p => p.date >= activeTrade.filingDate); return p ? <ReferenceDot x={p.date} y={p.close} r={7} stroke="var(--panel)" strokeWidth={3} fill={activeTrade.action === 'buy' ? '#69c7aa' : '#df9c78'}/> : null; })()}</AreaChart></ResponsiveContainer> : <p className="empty">{tr("Historical prices are unavailable for this symbol. It is not silently removed from the trade list.")}</p>}</div></section>
          <div className="metrics stock-metrics"><Metric label={tr("Close on the trade date")} term="rawPrice" value={money(tradePrice?.close)} detail={activeTrade ? shortDate(activeTrade.tradeDate) : tr('Select a disclosure')}/><Metric label={tr("Next open after filing")} term="nextOpen" value={money(disclosedPrice?.open)} detail={disclosedPrice ? shortDate(disclosedPrice.date) : tr('No matching session')}/><div className="metric"><span className="metric-label">{tr("Latest available quote")}<Help term="latestPrice"/></span><strong>{money(quote?.price)}</strong><small>{quote ? new Date(quote.asOf).toLocaleString(locale()) : tr('Not fetched — historical data is separate')}</small><button className="text-button" onClick={fetchQuote} disabled={quoting}>{quoting ? tr('Fetching…') : tr('Get latest quote')}</button></div></div>{quoteError && <div className="notice" role="status">{tr(quoteError)}</div>}
          <section className="panel"><div className="panel-heading"><h2>{tr("Disclosures for ")}{stock}<Help term="disclosure"/></h2><span className="subtle">{stockTrades.length}{tr(" records")}</span></div><div className="story-list">{stockTrades.map(t => <button key={t.id} className={`story-row ${activeTrade?.id === t.id ? 'selected' : ''}`} onClick={() => setSelectedTrade(t)}><span className={`trade-badge ${t.action}`}>{t.action === 'buy' ? tr('Buy') : tr('Sale')}</span><span><strong>{data.politicians.find(p => p.id === t.politician)?.name}</strong><small>{tr("Traded ")}{shortDate(t.tradeDate)}{tr(" \u00B7 filed ")}{shortDate(t.filingDate)}</small></span><span className="story-amount">{tr(t.amount)}</span><ChevronRight size={16}/></button>)}{!stockTrades.length && <p className="empty">{tr("No eligible disclosures for this selection.")}</p>}</div></section>
        </>}

        {tab === 'whatif' && <div className="whatif-layout"><section className="panel scenario-controls"><div className="panel-heading"><div><span className="eyebrow">{tr("BUILD YOUR SCENARIO")}</span><h2>{tr("The starting plan ")}<Help term="backtest"/></h2></div></div><div className="control-body"><label className="control-label">{tr("Who would you follow?")}<Help term="sleeve"/></label><div className="person-checks">{data.politicians.map((p, i) => <label key={p.id}><input type="checkbox" checked={settings.politicians.includes(p.id)} onChange={e => updateSettings({ politicians: e.target.checked ? [...settings.politicians, p.id] : settings.politicians.filter(n => n !== p.id) })}/><span className="person-dot" style={{ background: colors[i] }}/>{p.name}</label>)}</div><label className="form-field">{tr("Starting money")}<Help term="portfolio"/><div className="currency-input"><span>$</span><input aria-label={tr("Starting money")} type="number" min="1" max="100000000" value={settings.initial} onChange={e => updateSettings({ initial: Number(e.target.value) })}/></div></label><div className="date-inputs"><label>{tr("From")}<input aria-label={tr("Scenario start date")} type="date" min={data.coverageStart} max={data.coverageEnd} value={settings.start} onChange={e => updateSettings({ start: e.target.value })}/></label><label>{tr("To")}<input aria-label={tr("Scenario end date")} type="date" min={data.coverageStart} max={data.coverageEnd} value={settings.end} onChange={e => updateSettings({ end: e.target.value })}/></label></div><label className="form-field">{tr("Purchase rule")}<Help term="allocation"/><select aria-label={tr("Purchase rule")} value={`${settings.buyFraction}-${settings.sizing}`} onChange={e => { const [fraction, sizing] = e.target.value.split('-'); const n = Number(fraction); updateSettings({ buyFraction: n, capFraction: n === .02 ? .1 : n === .05 ? .2 : .3, sizing: sizing as SimulationSettings['sizing'] }); }}><option value="0.02-initial">{tr("2% of starting budget")}</option><option value="0.05-initial">{tr("5% of starting budget")}</option><option value="0.1-initial">{tr("10% of starting budget")}</option><option value="0.1-previous_close_equity">{tr("10% of prior account value")}</option></select></label><div className="rule-summary">{tr("Per-stock spending limit: ")}{settings.capFraction * 100}%<Help term="positionCap"/></div><label className="form-field">{tr("On a partial sale")}<Help term="partialSale"/><select aria-label={tr("Partial sale behavior")} value={settings.partialFraction} onChange={e => updateSettings({ partialFraction: Number(e.target.value) })}><option value="0.5">{tr("Sell half of our holding")}</option><option value="1">{tr("Sell all of our holding")}</option><option value="0.25">{tr("Sell a quarter of our holding")}</option></select></label><div className="date-inputs"><label>{tr("Extra wait ")}<Help term="executionDate"/><select aria-label={tr("Extra disclosure delay")} value={settings.extraDays} onChange={e => updateSettings({ extraDays: Number(e.target.value) })}><option value="0">{tr("Next market day")}</option><option value="3">{tr("3 extra days")}</option><option value="7">{tr("7 extra days")}</option></select></label><label>{tr("Cost per trade ")}<Help term="cost"/><select aria-label={tr("Trading cost")} value={settings.costPercent} onChange={e => updateSettings({ costPercent: Number(e.target.value) })}><option value="0">0%</option><option value="0.1">0.1%</option><option value="0.25">0.25%</option></select></label></div><button className="primary run-button" disabled={running || !settings.politicians.length} onClick={run}><FlaskConical size={18}/>{running ? tr('Calculating…') : tr('Run this what-if')}</button><button className="quiet save-button" onClick={() => { localStorage.setItem('capitol-scenario', JSON.stringify(settings)); setRefreshMessage('Scenario saved in this browser.'); }}>{tr("Save these settings")}</button><button className="quiet save-button" onClick={() => { try {
            const saved = localStorage.getItem('capitol-scenario');
            if (!saved) {
                setRefreshMessage('No saved scenario in this browser yet.');
                return;
            }
            const s = JSON.parse(saved);
            if (s && Array.isArray(s.politicians)) {
                setSettings(s);
                setDirty(true);
            }
        }
        catch {
            setRefreshMessage('The saved scenario could not be read.');
        } }}>{tr("Load saved settings")}</button></div></section>
          <div className="scenario-results">{runError && <div className="notice error" role="alert">{tr(runError)}</div>}{dirty && result && <div className="notice">{tr("Settings changed. Run again to update these results.")}</div>}{!result ? <section className="panel scenario-empty"><span className="empty-illustration"><FlaskConical size={38}/></span><div className="eyebrow">{tr("A LITTLE CURIOSITY GOES A LONG WAY")}</div><h2>{tr("Your what-if starts here.")}</h2><p>{tr("Pick your politicians and a budget, then run the scenario to see the path your money could have taken.")}</p><span className="subtle">{tr("Historical simulation ")}<Help term="backtest"/>{tr(" \u00B7 No real trades")}</span></section> : <><div className="metrics result-metrics"><Metric label={tr("Ending account value")} term="equity" value={money(result.endingValue, 0)} detail={tr(`${money(result.profit, 0)} change`)}/><Metric label={tr("Your return")} term="return" value={percent(result.returnPercent)} tone={result.returnPercent >= 0 ? 'buy-text' : 'sell-text'}/><Metric label={tr("SPY comparison")} term="spy" value={percent(result.benchmarkPercent)}/><Metric label={tr("Largest decline")} term="drawdown" value={`${result.maxDrawdownPercent.toFixed(2)}%`}/></div><section className="panel"><div className="panel-heading"><h2>{tr("Your money over time ")}<Help term="portfolio"/></h2><div className="legend"><span className="buy-text">{tr("\u25CF Your scenario")}</span><span>··· SPY</span></div></div><div className="chart-container"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.curve} margin={{ right: 20, left: 0, top: 10 }}><CartesianGrid vertical={false} stroke="var(--border)"/><XAxis dataKey="date" minTickGap={65} tickFormatter={d => String(d).slice(0, 7)} tick={{ fill: 'var(--muted)', fontSize: 12 }}/><YAxis tickFormatter={n => language === 'zh-CN' ? `$${(Number(n) / 10000).toFixed(1)}万` : `$${(Number(n) / 1000).toFixed(0)}k`} tick={{ fill: 'var(--muted)', fontSize: 12 }} width={60}/><Tooltip contentStyle={{ background: 'var(--panel)', borderColor: 'var(--border)' }} formatter={v => money(Number(v))}/><Line type="monotone" dataKey="equity" name={tr("Your account")} stroke="#69c7aa" strokeWidth={2.5} dot={false} isAnimationActive={false}/><Line dataKey="benchmark" name={tr("SPY comparison")} stroke="#a4aebb" strokeDasharray="5 5" strokeWidth={1.5} dot={false} isAnimationActive={false}/></LineChart></ResponsiveContainer></div><div className="result-footnote"><span>{tr("Average unspent cash: ")}<strong>{result.averageCashPercent.toFixed(1)}%</strong><Help term="cash"/></span><span>{result.orders.length}{tr(" simulated orders")}<Help term="executionDate"/></span></div></section><div className="notice">{tr("Historical results depend on these settings and the available data.")}<Help term="backtest"/>{result.audit.some(a => a.reason === 'missing_execution_price') && <strong>{tr(" Some orders were skipped because their prices were unavailable.")}<Help term="coverage"/></strong>}</div><section className="panel"><div className="panel-heading"><h2>{tr("The simulated orders")}<Help term="executionDate"/></h2></div><div className="table-scroll"><table><thead><tr><th>{tr("Date")}</th><th>{tr("Politician")}</th><th>{tr("Stock")}</th><th>{tr("Action")}</th><th>{tr("Cash amount")}</th><th>{tr("Source")}</th></tr></thead><tbody>{result.orders.map((o, i) => <tr key={`${o.sourceId}-${i}`}><td>{shortDate(o.date)}</td><td>{o.politician}</td><td><button className="stock-link" onClick={() => viewStock(o.ticker)}>{o.ticker}</button></td><td><span className={`trade-badge ${o.action}`}>{tr(o.action === 'buy' ? 'Buy' : 'Sell')}</span></td><td>{money(o.cashAmount)}</td><td><a href={o.sourceUrl} target="_blank" rel="noreferrer" aria-label={tr(`Source for simulated ${o.ticker} order`)}><ExternalLink size={15}/></a></td></tr>)}</tbody></table>{!result.orders.length && <p className="empty">{tr("These rules produced no orders in the selected period.")}</p>}</div></section></>}</div></div>}
        {tab === 'manual' && <Manual data={data} navigate={setTab}/>}<div hidden={tab !== 'chat'}><Chat data={data} configured={Boolean(status?.chatConfigured)} settings={settings} stock={stock} viewStock={viewStock}/></div><footer className="page-footer"><span><ShieldCheck size={14}/>{tr(" Private research \u00B7 No real trades")}</span><span>{tr("Official House filings \u00B7 Historical prices: Yahoo \u00B7 Latest quotes: Finnhub")}<Help term="coverage"/></span></footer>
      </main></div>
    <dialog ref={dictionaryRef} className="dictionary-dialog" onCancel={() => setDictionary(false)} onClick={e => { if (e.target === dictionaryRef.current)
        setDictionary(false); }}><div className="panel-heading"><div><span className="eyebrow">{tr("A LITTLE HELP, RIGHT WHERE YOU NEED IT")}</span><h2>{tr("Word help")}</h2></div><button className="icon-button" aria-label={tr("Close word help")} onClick={() => setDictionary(false)}><X /></button></div><label className="search-field"><Search size={18}/><input autoFocus aria-label={tr("Search dictionary")} placeholder={tr("Find a word…")} value={dictionarySearch} onChange={e => setDictionarySearch(e.target.value)}/></label><div className="dictionary-list">{(Object.keys(glossary) as GlossaryKey[]).filter(k => (tr(glossary[k].title) + ' ' + glossary[k].title).toLowerCase().includes(dictionarySearch.toLowerCase())).map(k => <div key={k}><span>{tr(glossary[k].title)}</span><Help term={k}/></div>)}</div></dialog>
  </div>;
}
