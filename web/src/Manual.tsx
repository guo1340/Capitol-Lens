import { Help } from './Help';
import { t, useLanguage } from './i18n';
import type { Dataset } from './types';
import { glossary, type GlossaryKey } from './glossary';

function ManualText({ text }: { text: string }) {
  const terms = Object.entries(glossary).flatMap(([key, entry]) => [
    { key: key as GlossaryKey, title: entry.title }, { key: key as GlossaryKey, title: t(entry.title) },
  ]);
  terms.push({ key: 'spy', title: 'SPY' }, { key: 'return', title: '收益率' },
    { key: 'filingDate', title: 'filing dates' }, { key: 'tradeDate', title: 'trade dates' });
  const patterns = [...new Set(terms.map(term => term.title))].sort((a, b) => b.length - a.length)
    .map(title => /[\u4e00-\u9fff]/.test(title) ? title : `\\b${title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`);
  return <>{text.split(new RegExp(`(${patterns.join('|')})`, 'gi')).map((part, i) => {
    const term = terms.find(item => item.title.toLowerCase() === part.toLowerCase());
    return term ? <span key={i}>{part}<Help term={term.key}/></span> : part;
  })}</>;
}

type Destination = 'explore' | 'stock' | 'whatif' | 'chat';
const sections: { id: string; title: string; term?: GlossaryKey; steps: string[]; destination?: Destination; button?: string }[] = [
  { id: 'start', title: 'Start here: a five-minute tour', steps: [
    'Sign in with your existing guopq admin account, then return to Capitol Lens. Hosted access is limited to guo1340@vt.edu; local development uses a clearly marked test identity.',
    'Read the historical coverage dates above before interpreting anything. Start in Explore trades and select one politician or search for a stock.',
    'Click a stock symbol to open Stock story. Select a disclosure and compare the trade date with the filing date and the next available opening price.',
    'Open What if, keep the initial settings for your first run, and click Run this what-if. Compare your result with SPY over the same dates.',
    'Open Chat with AI and ask for a simple summary. To discuss your chosen simulation, check Include my current what-if settings before sending.',
  ], destination: 'explore', button: 'Open Explore trades' },
  { id: 'explore', title: 'Explore trades: find a starting point', term: 'disclosure', steps: [
    'Search by stock symbol, company name or politician name. Combine the politician, buy/sell and filing-year filters to narrow the list.',
    'The cards and shared-stock table follow your filters. Click a buy/sell count to open that stock for the corresponding politician. A shared stock does not establish why anyone traded it.',
    'In Reported trades, compare the trade and filing dates. Use the source-link icon to open the original government filing. Show more trades reveals additional rows.',
    'Reported amounts are ranges, not your simulated purchase amounts. Household transactions can appear under the politician. Unsupported investments are excluded from the eligible-stock view.',
  ], destination: 'explore', button: 'Open Explore trades' },
  { id: 'stock', title: 'Stock story: read prices alongside disclosures', term: 'rawPrice', steps: [
    'Choose a stock and optionally one politician. Click a disclosure in the list to move the chart marker and update the date-specific price cards.',
    'Compare Close on the trade date with Next open after filing. The selected filing marker appears on the first available chart day on or after filing; the simulated opening price is strictly after filing.',
    'Click Get latest quote when you need the provider’s latest available price. Check its timestamp. This price is separate from the historical chart and is not automatically included in AI chat.',
    'If a price is unavailable, keep the missing-data message in mind. The app does not invent a value or remove the disclosure to hide the gap.',
  ], destination: 'stock', button: 'Open Stock story' },
  { id: 'simulate', title: 'What if: run a fair historical comparison', term: 'backtest', steps: [
    'Select one or more politicians, enter starting money in USD, and choose dates within the available coverage. Each run starts in cash; it does not carry earlier holdings into the selected period.',
    'Choose a purchase rule: 2%, 5% or 10% of starting budget, or 10% of the previous account value. The corresponding per-stock limits are 10%, 20%, 30% and 30%. Use the question marks beside these controls for the exact meaning.',
    'Choose what to sell after a partial-sale disclosure, an extra waiting period, and a cost per trade. Multiple politicians receive equal starting budgets and cannot share cash between their portions.',
    'Click Run this what-if. Read the ending account value, your return, SPY comparison, largest decline, unspent cash and simulated order list together. Open an order’s source link to check its filing.',
    'Change only one setting at a time and rerun to compare its effect. After settings change, the existing results remain from the previous run until you run again.',
    'Save these settings stores one scenario in this browser. Load saved settings restores it. This does not save a result history or synchronize settings across devices.',
  ], destination: 'whatif', button: 'Open What if' },
  { id: 'chat', title: 'Chat with AI: ask in everyday language', term: 'aiResearch', steps: [
    'Choose a suggested question or type up to 2,000 characters, then click Send question. Useful questions include: What stands out? Which stocks deserve more research? What could go wrong?',
    'Check Include my current what-if settings to have the backend recalculate that scenario for the answer. Without this option, the chat does not receive a calculated copy-strategy result.',
    'Read the dated evidence and source chips under the answer. A source chip opens a stock view or an original filing. Historical price increases and frequent politician purchases do not prove a stock is a good buy today.',
    'Chat uses the stored research snapshot, not live quotes, current news or your Webull account. Ask about missing evidence and downside risks as well as possible opportunities.',
    'The language switch controls new answers. Company and politician names stay in English. Existing messages keep their original wording. New chat or reloading clears the conversation; switching tabs does not.',
    'Sending a question uses your OpenAI API allowance. Stop cancels waiting in the interface but may not cancel provider processing or charges. Never paste an API key into the conversation.',
  ], destination: 'chat', button: 'Open Chat with AI' },
  { id: 'data', title: 'Dates, data updates and limitations', term: 'snapshot', steps: [
    'Historical coverage shows the stored date range. Snapshot built is when the data file was generated. A recent build date does not mean the market data is current.',
    'Refresh data requests the GitHub update workflow. It does not immediately replace the page’s data. Follow View update progress, wait for the workflow and Cloudflare deployment to succeed, then reload.',
    'The scheduled update is configured for 03:23 UTC each day. GitHub Actions and the deployment connection must be enabled; schedules can be delayed. Running the local frontend alone does not fetch new government reports.',
    'If extraction or held-price checks fail, the update keeps the previous published snapshot. Check the failed workflow rather than assuming an unchanged date means no new trades occurred.',
    'Government filing dates are a proxy for public availability, not verified publication timestamps. Historical prices come from the existing Yahoo research feed; latest quote requests use Finnhub.',
    'Past results depend on the chosen people, dates, rules and available prices. The model does not include taxes or every real-world execution constraint. Capitol Lens cannot connect to Webull or place real orders in stage 1.',
  ] },
  { id: 'preferences', title: 'Language, display and word help', steps: [
    'Click 中文 or English in the top bar to change the interface language. Your choice is remembered in this browser. Original company names, politician names, stock symbols and USD amounts stay unchanged.',
    'Use the sun/moon button for light or dark mode. The setting also applies to charts, the dictionary and this manual.',
    'Hover over a small question mark, focus it with the keyboard, or tap it to read the central dictionary explanation. Press Escape to dismiss it. Open Word help to search the full dictionary in English or Chinese.',
  ] },
  { id: 'troubleshooting', title: 'If something does not work', steps: [
    'Not found at a custom domain: the currently supported hosted address is api.guopq.com/capitol-lens/. Adding a different domain alone does not change the app’s paths or move its login cookie.',
    'Access denied: sign in at admin.guopq.com with guo1340@vt.edu, return to the app and reload. If verification is unavailable, the administrator should check the ADMIN service binding to guopq-admin.',
    'Local page cannot load data: start npm run dev:backend and npm run dev in separate terminals inside web. For a first setup, run npm ci and npm run build before starting the backend.',
    'Chat not connected: configure the exact backend secret name OPENAI_API_KEY. Local keys belong in web/.dev.vars; hosted keys belong in the Worker’s runtime Variables & Secrets. Restart the backend or save/deploy the hosted change, then reload.',
    'AI reports a credit or rate limit: check the API organization associated with the key, its credit balance and model limits. A claimed Pro benefit must fund that same organization. Try again after the reported limit clears.',
    'Latest quote unavailable: check FINNHUB_API_KEY on the backend and the provider response. Historical exploration can still work without this key.',
    'Refresh not configured: the administrator must configure GITHUB_TOKEN with permission to dispatch the repository workflow. An accepted request still needs a successful workflow and deployment.',
    'A simulation stops or skips an order: inspect the displayed missing-data or settings message. Do not treat an incomplete result as a complete comparison.',
  ] },
];

export function Manual({ data, navigate }: { data: Dataset; navigate: (tab: Destination) => void }) {
  useLanguage();
  return <div className="manual-layout">
    <nav className="panel manual-toc" aria-label={t('Manual contents')}><h2>{t('In this guide')}</h2>{sections.map((section, index) => <a href={`#guide-${section.id}`} key={section.id}>{index + 1}. {t(section.title)}</a>)}</nav>
    <article className="manual-body">
      <section className="panel manual-intro"><span className="eyebrow">{t('A practical guide to Capitol Lens')}</span><h2>{t('Learn the app, one step at a time.')}</h2><p>{t('Use this guide alongside the app. Open a section, try its steps, then return here whenever you need help.')}</p><p>{t('Your current data covers')} <strong>{data.coverageStart} — {data.coverageEnd}</strong>.<Help term="coverage"/></p><a href="https://github.com/guo1340/Capitol-Lens/blob/main/web/README.md" target="_blank" rel="noreferrer">{t('Administrator setup instructions on GitHub')}</a></section>
      {sections.map((section, index) => <section className="panel manual-section" id={`guide-${section.id}`} key={section.id}>
        <h2>{index + 1}. {t(section.title)}{section.term && <Help term={section.term}/>}</h2>
        <ol>{section.steps.map(step => <li key={step}><ManualText text={t(step)}/></li>)}</ol>
        {section.destination && <button className="secondary" onClick={() => navigate(section.destination!)}>{t(section.button!)}</button>}
      </section>)}
    </article>
  </div>;
}
