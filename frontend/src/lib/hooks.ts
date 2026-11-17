import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  const load = useCallback(async () => {
    if (!path) { setLoading(false); return; }
    setLoading(true); setError(null);
    try { setData(await api.get<T>(path)); } catch (e) { setError((e as Error).message); }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load, setData };
}

export function useTheme() {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem("agriguard_theme") === "dark"; } catch { return false; }
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("agriguard_theme", dark ? "dark" : "light"); } catch { /* ignore */ }
  }, [dark]);
  return { dark, toggle: () => setDark((d) => !d) };
}

export const fmtDate = (s: string) =>
  new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z").toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
export const fmtDay = (s: string) =>
  new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z").toLocaleDateString(undefined, { day: "numeric", month: "short" });
export const pct = (v: number | null | undefined, d = 0) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`);
export const titleCase = (s: string) => s.replace(/\b\w/g, (c) => c.toUpperCase());
