import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore, type User } from "./api";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; phone?: string; language: string }) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) { setUser(null); setLoading(false); return; }
    try { setUser(await api.get<User>("/api/auth/me")); } catch { setUser(null); }
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const onLogout = () => setUser(null);
    window.addEventListener("agriguard:logout", onLogout);
    return () => window.removeEventListener("agriguard:logout", onLogout);
  }, [refresh]);

  const login = async (email: string, password: string) => {
    const r = await api.post<{ access_token: string; user: User }>("/api/auth/login", { email, password });
    tokenStore.set(r.access_token); setUser(r.user);
  };
  const register: AuthCtx["register"] = async (data) => {
    const r = await api.post<{ access_token: string; user: User }>("/api/auth/register", data);
    tokenStore.set(r.access_token); setUser(r.user);
  };
  const logout = () => { tokenStore.clear(); setUser(null); };

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
