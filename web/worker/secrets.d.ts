/** Optional runtime secrets set with wrangler secret put; not plaintext vars. */
interface Env {
  FINNHUB_API_KEY?: string;
  GITHUB_TOKEN?: string;
}
