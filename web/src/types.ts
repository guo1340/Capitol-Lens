export interface Politician {
  id: string;
  name: string;
  district: string;
  filingCount: number;
}
export interface Trade {
  id: string;
  politician: string;
  ticker: string | null;
  action: 'buy' | 'sell' | 'exchange';
  partial: boolean;
  tradeDate: string;
  filingDate: string;
  amount: string;
  assetType: string | null;
  excludedReason: string | null;
  sourceUrl: string;
}
export interface DailyPrice {
  date: string;
  open: number;
  close: number;
  adjustedOpen: number;
  adjustedClose: number;
}
export interface Dataset {
  schemaVersion: 1;
  builtAt: string;
  coverageStart: string;
  coverageEnd: string;
  politicians: Politician[];
  trades: Trade[];
  prices: Record<string, DailyPrice[]>;
  priceErrors: Record<string, string>;
  source: string;
  sourceIssues: number;
  companies: Record<string, string>;
}
export interface SimulationSettings {
  politicians: string[];
  start: string;
  end: string;
  initial: number;
  buyFraction: number;
  capFraction: number;
  sizing: 'initial' | 'previous_close_equity';
  costPercent: number;
  partialFraction: number;
  extraDays: number;
}
export interface Order {
  date: string;
  politician: string;
  ticker: string;
  action: 'buy' | 'sell';
  cashAmount: number;
  sourceId: string;
  sourceUrl: string;
}
export interface SimulationResult {
  endingValue: number;
  profit: number;
  returnPercent: number;
  benchmarkPercent: number;
  maxDrawdownPercent: number;
  averageCashPercent: number;
  realizedProfit: number;
  unrealizedProfit: number;
  costs: number;
  orders: Order[];
  curve: { date: string; equity: number; cash: number; benchmark: number }[];
  audit: { reason: string; date?: string; ticker?: string; sourceId?: string }[];
}
