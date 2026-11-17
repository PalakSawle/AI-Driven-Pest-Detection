import clsx from "clsx";
import { motion } from "framer-motion";
import { AlertTriangle, Loader2, Sprout } from "lucide-react";
import { useState, type ReactNode } from "react";
import { fileUrl, type Instance, type Level } from "../lib/api";
import { titleCase } from "../lib/hooks";

export const LEVEL_META: Record<string, { label: string; color: string; bg: string; text: string }> = {
  safe: { label: "Safe", color: "#15803d", bg: "bg-green-100 dark:bg-green-500/15", text: "text-green-800 dark:text-green-300" },
  none: { label: "None", color: "#15803d", bg: "bg-green-100 dark:bg-green-500/15", text: "text-green-800 dark:text-green-300" },
  low: { label: "Low", color: "#65a30d", bg: "bg-lime-100 dark:bg-lime-500/15", text: "text-lime-800 dark:text-lime-300" },
  moderate: { label: "Moderate", color: "#ca8a04", bg: "bg-yellow-100 dark:bg-yellow-500/15", text: "text-yellow-800 dark:text-yellow-300" },
  high: { label: "High", color: "#ea580c", bg: "bg-orange-100 dark:bg-orange-500/15", text: "text-orange-800 dark:text-orange-300" },
  critical: { label: "Critical", color: "#dc2626", bg: "bg-red-100 dark:bg-red-500/15", text: "text-red-800 dark:text-red-300" },
};

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("card p-5", className)}>{children}</div>;
}

export function PageHeader({ title, subtitle, actions, eyebrow }: { title: string; subtitle?: string; actions?: ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <div className="mb-1 text-xs font-semibold uppercase tracking-[.14em] text-forest-500">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold text-forest-950 sm:text-3xl dark:text-white">{title}</h1>
        {subtitle && <p className="muted mt-1 max-w-2xl text-sm">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Stat({ label, value, icon, hint, tone = "forest" }: { label: string; value: ReactNode; icon: ReactNode; hint?: string; tone?: "forest" | "amber" | "red" }) {
  const tones = { forest: "bg-forest-100 text-forest-700 dark:bg-forest-500/15 dark:text-forest-300", amber: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300", red: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300" };
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
      <div className="flex items-start justify-between">
        <div className="text-xs font-semibold uppercase tracking-wide text-forest-900/55 dark:text-forest-100/55">{label}</div>
        <div className={clsx("rounded-xl p-2", tones[tone])}>{icon}</div>
      </div>
      <div className="mt-3 truncate font-display text-3xl font-semibold">{value}</div>
      {hint && <div className="muted mt-1 truncate text-xs">{hint}</div>}
    </motion.div>
  );
}

export function LevelBadge({ level, score }: { level?: string | null; score?: number | null }) {
  if (!level) return <span className="chip bg-forest-100 text-forest-700 dark:bg-white/5 dark:text-forest-200">—</span>;
  const m = LEVEL_META[level] ?? LEVEL_META.low;
  return (
    <span className={clsx("chip", m.bg, m.text)}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
      {m.label}{score != null && ` · ${score.toFixed(0)}`}
    </span>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="flex items-center justify-center gap-2 py-16 text-sm text-forest-700 dark:text-forest-200"><Loader2 className="h-5 w-5 animate-spin" />{label}</div>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && <button className="font-semibold underline" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Empty({ title, body, action, icon }: { title: string; body?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-forest-900/15 px-6 py-14 text-center dark:border-white/10">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-forest-100 text-forest-700 dark:bg-forest-500/15 dark:text-forest-300">{icon ?? <Sprout className="h-7 w-7" />}</div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {body && <p className="muted mt-1 max-w-sm text-sm">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/** Semicircular gauge: Safe → Critical. */
export function SeverityMeter({ score, level, size = 220 }: { score: number; level: Level | string; size?: number }) {
  const segs = [["safe", 0, 5], ["low", 5, 25], ["moderate", 25, 50], ["high", 50, 75], ["critical", 75, 100]] as const;
  const r = 80, cx = 100, cy = 100;
  const pt = (v: number, rad = r) => { const a = Math.PI * (1 - v / 100); return [cx + rad * Math.cos(a), cy - rad * Math.sin(a)]; };
  const arc = (a: number, b: number) => { const [x1, y1] = pt(a); const [x2, y2] = pt(b); return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`; };
  const [nx, ny] = pt(Math.max(0, Math.min(100, score)), 62);
  const m = LEVEL_META[level] ?? LEVEL_META.low;
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" width={size} height={size * 0.6} role="img" aria-label={`Severity ${score} of 100, ${m.label}`}>
        {segs.map(([k, a, b]) => <path key={k} d={arc(a + 0.6, b - 0.6)} stroke={LEVEL_META[k].color} strokeWidth="16" fill="none" strokeLinecap="butt" opacity={k === level ? 1 : 0.28} />)}
        <motion.line x1={cx} y1={cy} initial={{ x2: cx - 62, y2: cy }} animate={{ x2: nx, y2: ny }} transition={{ type: "spring", stiffness: 60, damping: 12 }} stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" className="text-forest-950 dark:text-white" />
        <circle cx={cx} cy={cy} r="7" className="fill-forest-950 dark:fill-white" />
      </svg>
      <div className="-mt-2 text-center">
        <div className="font-display text-4xl font-semibold" style={{ color: m.color }}>{score.toFixed(0)}<span className="text-base text-forest-900/40 dark:text-white/40">/100</span></div>
        <div className="mt-0.5 text-sm font-semibold uppercase tracking-wide" style={{ color: m.color }}>{m.label} risk</div>
      </div>
    </div>
  );
}

/** Original image with interactive SVG boxes (hover to highlight). */
export function DetectionImage({ src, width, height, instances, showBoxes = true }: { src: string; width: number; height: number; instances: Instance[]; showBoxes?: boolean }) {
  const [hover, setHover] = useState<number | null>(null);
  const classes = [...new Set(instances.map((i) => i.pest_class))];
  const colors = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0891b2", "#2563eb", "#7c3aed", "#db2777"];
  return (
    <div className="relative overflow-hidden rounded-xl bg-forest-950">
      <img src={fileUrl(src)} alt="Uploaded crop" className="block h-auto w-full" />
      {showBoxes && (
        <svg viewBox={`0 0 ${width} ${height}`} className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
          {instances.map((b) => {
            const c = colors[classes.indexOf(b.pest_class) % colors.length];
            const active = hover === b.id;
            return (
              <g key={b.id} onMouseEnter={() => setHover(b.id)} onMouseLeave={() => setHover(null)}>
                <rect x={b.x1} y={b.y1} width={b.x2 - b.x1} height={b.y2 - b.y1} fill={active ? c + "33" : "transparent"} stroke={c} strokeWidth={Math.max(2, width / 300)} strokeDasharray={b.low_confidence ? `${width / 100} ${width / 160}` : undefined} vectorEffect="non-scaling-stroke" style={{ strokeWidth: active ? 3.5 : 2.5 }} />
                {active && <title>{`${titleCase(b.pest_class)} ${(b.confidence * 100).toFixed(1)}%`}</title>}
              </g>
            );
          })}
        </svg>
      )}
      {hover != null && (() => { const b = instances.find((i) => i.id === hover)!; return (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-black/75 px-2.5 py-1.5 text-xs font-medium text-white">{titleCase(b.pest_class)} · {(b.confidence * 100).toFixed(1)}%{b.low_confidence && " · low confidence"}</div>
      ); })()}
    </div>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 0.7 ? "bg-forest-500" : value >= 0.4 ? "bg-yellow-500" : "bg-orange-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-forest-900/10 dark:bg-white/10"><div className={clsx("h-full rounded-full", color)} style={{ width: `${value * 100}%` }} /></div>
      <span className="w-12 text-right text-xs tabular-nums">{(value * 100).toFixed(1)}%</span>
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} className="inline-flex items-center gap-2 text-sm">
      <span className={clsx("relative h-5 w-9 rounded-full transition", checked ? "bg-forest-600" : "bg-forest-900/20 dark:bg-white/15")}>
        <span className={clsx("absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all", checked ? "left-[18px]" : "left-0.5")} />
      </span>
      {label}
    </button>
  );
}
