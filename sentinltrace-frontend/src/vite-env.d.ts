/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * CARTO Basemaps API key. Free, client-side, fair-use-limited — required
   * by CARTO's basemap tile endpoints as of their 2026 API-key rollout.
   * Get one at https://carto.com/basemaps/apikey (no CARTO account needed).
   * Set it in .env.local, which is git-ignored. Never commit a real value.
   */
  readonly VITE_CARTO_API_KEY: string;

  /**
   * Base URL of the SentinelTrace FastAPI backend, e.g.
   * http://127.0.0.1:8000 for local development. Read by
   * src/services/httpClient.ts. Set it in .env.local (git-ignored) —
   * see .env.example. Never hardcode a production URL in source.
   */
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
