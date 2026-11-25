import type { Dataset, SimulationResult, SimulationSettings, Trade } from './types';

const addDays = (day: string, days: number) => {
  const value = new Date(`${day}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
};

/** Browser-compatible, deterministic port of the audited Python simulator. */
export function simulate(data: Dataset, settings: SimulationSettings): SimulationResult {
  const names = [...new Set(settings.politicians)].sort();
  const numeric = [settings.initial, settings.buyFraction, settings.capFraction, settings.costPercent, settings.partialFraction, settings.extraDays];
  if (numeric.some(n => !Number.isFinite(n)) || settings.initial <= 0 || settings.initial > 100_000_000 ||
      !names.length || names.some(n => !data.politicians.some(p => p.id === n)) ||
      settings.buyFraction <= 0 || settings.buyFraction > settings.capFraction || settings.capFraction > 1 ||
      settings.costPercent < 0 || settings.costPercent >= 100 || settings.partialFraction <= 0 || settings.partialFraction > 1 ||
      !Number.isInteger(settings.extraDays) || settings.extraDays < 0 || settings.extraDays > 90 ||
      settings.start < data.coverageStart || settings.end > data.coverageEnd || settings.start > settings.end ||
      !['initial', 'previous_close_equity'].includes(settings.sizing)) throw new Error('Choose valid dates, politicians and allocation settings within the available data.');
  if (data.sourceIssues > 0) throw new Error('Some source reports need review. This snapshot cannot produce a complete what-if result.');
  const histories = new Map(Object.entries(data.prices).map(([ticker, days]) => [ticker, new Map(days.map(day => [day.date, day]))]));
  const calendar = (data.prices.SPY ?? []).map(p => p.date).filter(d => d >= settings.start && d <= settings.end).sort();
  if (!calendar.length) throw new Error('No comparison prices are available in this date range.');
  const result: SimulationResult = { endingValue: 0, profit: 0, returnPercent: 0, benchmarkPercent: 0,
    maxDrawdownPercent: 0, averageCashPercent: 0, realizedProfit: 0, unrealizedProfit: 0, costs: 0, orders: [], curve: [], audit: [] };
  const grouped = new Map<string, Trade[]>();
  for (const trade of data.trades) {
    if (!names.includes(trade.politician) || trade.excludedReason || !trade.ticker || trade.filingDate < settings.start || trade.filingDate > settings.end) continue;
    const available = addDays(trade.filingDate, settings.extraDays);
    const day = calendar.find(d => d > available);
    if (!day) { result.audit.push({ reason: 'execution_after_end', sourceId: trade.id }); continue; }
    const key = `${day}|${trade.politician}|${trade.ticker}`;
    grouped.set(key, [...(grouped.get(key) ?? []), trade]);
  }
  const schedule = new Map<string, Trade[]>();
  for (const [key, batch] of [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const [day, , ticker] = key.split('|');
    const latest = batch.map(t => t.tradeDate).sort().at(-1)!;
    const candidates = batch.filter(t => t.tradeDate === latest);
    if (new Set(candidates.map(t => t.action)).size > 1) { result.audit.push({ reason: 'ambiguous_same_day_buy_and_sell', date: day, ticker }); continue; }
    const chosen = candidates.sort((a, b) => Number(a.partial) - Number(b.partial) || a.id.localeCompare(b.id))[0];
    schedule.set(day, [...(schedule.get(day) ?? []), chosen]);
    if (batch.length > 1) result.audit.push({ reason: 'collapsed_same_session_signals', date: day, ticker, sourceId: chosen.id });
  }
  const sleeve = settings.initial / names.length;
  const cash = Object.fromEntries(names.map(n => [n, sleeve]));
  let sizingEquity = { ...cash };
  const holdings = new Map<string, { politician: string; ticker: string; units: number; basis: number }>();
  const cost = settings.costPercent / 100;
  const benchmarkUnits = settings.initial / (histories.get('SPY')!.get(calendar[0])!.adjustedOpen * (1 + cost));
  let peak = settings.initial;
  for (const day of calendar) {
    const valid: Trade[] = [];
    for (const trade of schedule.get(day) ?? []) {
      const key = `${trade.politician}|${trade.ticker}`;
      if (trade.action === 'sell' && (holdings.get(key)?.units ?? 0) <= 1e-12) {
        result.audit.push({ reason: 'sell_without_strategy_position', date: day, sourceId: trade.id }); continue;
      }
      if (!histories.get(trade.ticker!)?.has(day)) {
        result.audit.push({ reason: 'missing_execution_price', date: day, ticker: trade.ticker!, sourceId: trade.id }); continue;
      }
      valid.push(trade);
    }
    for (const trade of valid.filter(t => t.action === 'sell')) {
      const holding = holdings.get(`${trade.politician}|${trade.ticker}`)!;
      const fraction = trade.partial ? settings.partialFraction : 1;
      const quantity = holding.units * fraction;
      const gross = quantity * histories.get(trade.ticker!)!.get(day)!.adjustedOpen;
      const proceeds = gross * (1 - cost);
      const basis = holding.basis * fraction;
      holding.units -= quantity; holding.basis -= basis;
      cash[trade.politician] += proceeds;
      result.realizedProfit += proceeds - basis; result.costs += gross * cost;
      result.orders.push({ date: day, politician: trade.politician, ticker: trade.ticker!, action: 'sell', cashAmount: proceeds, sourceId: trade.id, sourceUrl: trade.sourceUrl });
    }
    for (const name of names) {
      const capital = settings.sizing === 'initial' ? sleeve : sizingEquity[name];
      const requests = valid.filter(t => t.action === 'buy' && t.politician === name).map(trade => ({ trade,
        budget: Math.max(0, Math.min(capital * settings.buyFraction, capital * settings.capFraction - (holdings.get(`${name}|${trade.ticker}`)?.basis ?? 0))) }));
      const total = requests.reduce((sum, r) => sum + r.budget, 0);
      const scale = total ? Math.min(1, cash[name] / total) : 0;
      for (const { trade, budget } of requests) {
        const spend = budget * scale;
        if (spend <= 1e-8) { result.audit.push({ reason: 'no_cash_or_position_cap', date: day, sourceId: trade.id }); continue; }
        const key = `${name}|${trade.ticker}`;
        const price = histories.get(trade.ticker!)!.get(day)!.adjustedOpen;
        const units = spend / (price * (1 + cost));
        const holding = holdings.get(key) ?? { politician: name, ticker: trade.ticker!, units: 0, basis: 0 };
        holding.units += units; holding.basis += spend; holdings.set(key, holding);
        cash[name] -= spend; result.costs += spend - units * price;
        result.orders.push({ date: day, politician: name, ticker: trade.ticker!, action: 'buy', cashAmount: spend, sourceId: trade.id, sourceUrl: trade.sourceUrl });
      }
    }
    sizingEquity = { ...cash };
    for (const holding of holdings.values()) {
      if (holding.units <= 1e-12) continue;
      const price = histories.get(holding.ticker)?.get(day);
      if (!price) throw new Error(`Missing price for held stock ${holding.ticker} on ${day}. The result has been stopped rather than hiding this holding.`);
      sizingEquity[holding.politician] += holding.units * price.adjustedClose;
    }
    const equity = Object.values(sizingEquity).reduce((a, b) => a + b, 0);
    const totalCash = Object.values(cash).reduce((a, b) => a + b, 0);
    if (totalCash < -1e-6) throw new Error('The simulation exceeded its cash budget.');
    peak = Math.max(peak, equity);
    result.maxDrawdownPercent = Math.min(result.maxDrawdownPercent, (equity / peak - 1) * 100);
    result.curve.push({ date: day, equity, cash: totalCash, benchmark: benchmarkUnits * histories.get('SPY')!.get(day)!.adjustedClose });
  }
  const final = result.curve.at(-1)!;
  result.endingValue = final.equity;
  result.profit = final.equity - settings.initial;
  result.returnPercent = result.profit / settings.initial * 100;
  result.benchmarkPercent = (final.benchmark / settings.initial - 1) * 100;
  result.averageCashPercent = result.curve.reduce((sum, p) => sum + p.cash / p.equity, 0) / result.curve.length * 100;
  result.unrealizedProfit = [...holdings.values()].reduce((sum, h) => sum + (h.units > 1e-12 ? h.units * histories.get(h.ticker)!.get(calendar.at(-1)!)!.adjustedClose - h.basis : 0), 0);
  if (Math.abs(result.realizedProfit + result.unrealizedProfit - result.profit) > Math.max(1e-6, settings.initial * 1e-10)) throw new Error('The simulation did not reconcile.');
  return result;
}
