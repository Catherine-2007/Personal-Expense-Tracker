import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "./api";

const CurrencyRatesContext = createContext(null);
const STORAGE_KEY = "ss_fx_rates_cache";
const MAX_AGE_MS = 6 * 3600 * 1000; // matches backend cache TTL

export function CurrencyRatesProvider({ children }) {
  const [rates, setRates] = useState(null);
  const [meta, setMeta] = useState(null); // { source, fetched_at, fallback_dated }
  const [loading, setLoading] = useState(false);

  const fetchRates = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/fx/rates");
      setRates(data.rates);
      setMeta({ source: data.source, fetched_at: data.fetched_at, fallback_dated: data.fallback_dated });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ rates: data.rates, meta: data, cachedAt: Date.now() }));
    } catch {
      // If the request itself fails (e.g. not logged in yet), fall back to
      // whatever was last cached locally so the app still shows numbers.
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        setRates(parsed.rates);
        setMeta(parsed.meta);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (Date.now() - parsed.cachedAt < MAX_AGE_MS) {
        setRates(parsed.rates);
        setMeta(parsed.meta);
        return; // still fresh, skip immediate refetch
      }
    }
    // Skip the initial fetch entirely if there's no session yet — the
    // endpoint requires auth, and attempting it pre-login would trigger
    // the 401 interceptor and bounce the user off the Register page.
    // App.jsx re-triggers this once a user is actually signed in.
    if (localStorage.getItem("ss_token")) {
      fetchRates();
    }
  }, [fetchRates]);

  return (
    <CurrencyRatesContext.Provider value={{ rates, meta, loading, refresh: fetchRates }}>
      {children}
    </CurrencyRatesContext.Provider>
  );
}

export function useCurrencyRates() {
  return useContext(CurrencyRatesContext);
}
