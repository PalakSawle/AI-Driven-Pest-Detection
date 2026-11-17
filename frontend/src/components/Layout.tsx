import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3, Bell, Bot, CloudSun, History, LayoutDashboard, Leaf, LogOut, Menu, Moon, ScanSearch, Settings, ShieldCheck, Sun, X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/hooks";

const NAV = [
  { to: "/app", label: "Dashboard", hi: "डैशबोर्ड", icon: LayoutDashboard, end: true },
  { to: "/app/detect", label: "Detect pests", hi: "कीट पहचान", icon: ScanSearch },
  { to: "/app/history", label: "History", hi: "इतिहास", icon: History },
  { to: "/app/analytics", label: "Analytics", hi: "विश्लेषण", icon: BarChart3 },
  { to: "/app/treatments", label: "Treatments", hi: "उपचार", icon: Leaf },
  { to: "/app/chat", label: "AI Kisan", hi: "AI किसान", icon: Bot },
  { to: "/app/weather", label: "Weather", hi: "मौसम", icon: CloudSun },
  { to: "/app/alerts", label: "Alerts", hi: "अलर्ट", icon: Bell },
  { to: "/app/profile", label: "Settings", hi: "सेटिंग्स", icon: Settings },
];

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-forest-800 text-forest-200 shadow-soft"><Leaf className="h-5 w-5" /></div>
      <div className={clsx("font-display text-lg font-semibold leading-none", light ? "text-white" : "text-forest-950 dark:text-white")}>
        AgriGuard<span className="text-forest-500"> AI</span>
      </div>
    </Link>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const loc = useLocation();
  const showHindi = user?.language !== "en";

  useEffect(() => { setOpen(false); }, [loc.pathname]);
  useEffect(() => {
    let alive = true;
    const load = () => api.get<{ count: number }>("/api/alerts/unread-count").then((r) => alive && setUnread(r.count)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    window.addEventListener("agriguard:alerts", load);
    return () => { alive = false; clearInterval(t); window.removeEventListener("agriguard:alerts", load); };
  }, []);

  const nav = (
    <nav className="flex flex-1 flex-col gap-1">
      {NAV.map(({ to, label, hi, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} className={({ isActive }) => clsx(
          "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
          isActive ? "bg-forest-800 text-white shadow-soft dark:bg-forest-500/20 dark:text-forest-100" : "text-forest-900/70 hover:bg-forest-100 hover:text-forest-900 dark:text-forest-100/70 dark:hover:bg-white/5")}>
          <Icon className="h-[18px] w-[18px]" />
          <span className="flex-1">{label}{showHindi && <span className="ml-1.5 text-[11px] opacity-60">{hi}</span>}</span>
          {to === "/app/alerts" && unread > 0 && <span className="rounded-full bg-red-600 px-1.5 text-[11px] font-bold text-white">{unread}</span>}
        </NavLink>
      ))}
      {user?.role === "admin" && (
        <NavLink to="/app/admin" className={({ isActive }) => clsx("mt-2 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium", isActive ? "bg-forest-800 text-white" : "text-forest-900/70 hover:bg-forest-100 dark:text-forest-100/70 dark:hover:bg-white/5")}>
          <ShieldCheck className="h-[18px] w-[18px]" /> Admin
        </NavLink>
      )}
    </nav>
  );

  const footer = (
    <div className="mt-6 border-t border-forest-900/10 pt-4 dark:border-white/10">
      <div className="flex items-center gap-3 px-1">
        <div className="grid h-9 w-9 place-items-center rounded-full bg-forest-200 font-semibold text-forest-800 dark:bg-forest-500/20 dark:text-forest-200">{user?.full_name?.[0]?.toUpperCase()}</div>
        <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{user?.full_name}</div><div className="muted truncate text-xs">{user?.email}</div></div>
        <button onClick={logout} className="btn-ghost !p-2" aria-label="Log out" title="Log out"><LogOut className="h-4 w-4" /></button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-forest-900/[.07] bg-cream-100/60 p-4 backdrop-blur lg:flex dark:border-white/[.06] dark:bg-[#0e1912]">
        <div className="mb-6 px-1 pt-1"><Logo /></div>{nav}{footer}
      </aside>
      <AnimatePresence>
        {open && (
          <>
            <motion.div className="fixed inset-0 z-40 bg-black/40 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} />
            <motion.aside className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-cream-50 p-4 lg:hidden dark:bg-[#0e1912]" initial={{ x: -300 }} animate={{ x: 0 }} exit={{ x: -300 }} transition={{ type: "spring", damping: 26, stiffness: 260 }}>
              <div className="mb-6 flex items-center justify-between"><Logo /><button className="btn-ghost !p-2" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button></div>
              {nav}{footer}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
      <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-forest-900/[.06] bg-cream-50/80 px-4 backdrop-blur sm:px-6 dark:border-white/[.06] dark:bg-[#0b140e]/80">
        <button className="btn-ghost !p-2 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
        <div className="lg:hidden"><Logo /></div>
        <div className="flex-1" />
        <Link to="/app/detect" className="btn-primary hidden sm:inline-flex"><ScanSearch className="h-4 w-4" />New scan</Link>
        <Link to="/app/alerts" className="btn-ghost relative !p-2" aria-label="Alerts">
          <Bell className="h-5 w-5" />
          {unread > 0 && <span className="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-600 ring-2 ring-cream-50 dark:ring-[#0b140e]" />}
        </Link>
        <button className="btn-ghost !p-2" onClick={toggle} aria-label="Toggle dark mode">{dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8"><Outlet /></main>
    </div>
  );
}
