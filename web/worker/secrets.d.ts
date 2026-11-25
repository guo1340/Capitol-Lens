/** Optional runtime secrets set with wrangler secret put; not plaintext vars. */
interface Env {
  FINNHUB_API_KEY?: string;
  GITHUB_TOKEN?: string;
  OPENAI_API_KEY?: string;
  OPENAI_MODEL?: string;
}
