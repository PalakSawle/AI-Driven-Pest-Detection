import { AlertTriangle, ArrowRight, Bug, CloudSun, Percent, ScanSearch, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Empty, ErrorBox, LEVEL_META, LevelBadge, PageHeader, Spinner, Stat } from "../components/ui";
import type { Notification, Overview, Trends } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate, pct, titleCase, useApi } from "../lib/hooks";

export const tooltipStyle = { contentStyle: { borderRadius: 12, border: "1px solid rgba(27,55,35,.1)", fontSize: 12 } };

export default function Dashboard() {
  const { user } = useAuth();
  const ov = useApi<Overview>("/api/analytics/overview");
  const tr = useApi<Trends>("/api/analytics/trends?period=daily&days=30");
  const alerts = useApi<Notification[]>("/api/alerts?limit=20");
  const wx = useApi<{ status: string; current?: { temperature_c: number; humidity_pct: number; rainfall_mm: number; description: string }; pest_risk?: { risk: string; title: string }[] }>("/api/weather");
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  if (ov.loading) return <Spinner />;
  if (ov.error) return <ErrorBox message={ov.error} onRetry={ov.reload} />;
  const o = ov.data!;
  const densityAlerts = (alerts.data ?? []).filter((a) => a.level === "high" || a.level === "critical").slice(0, 4);

  return (
    <div>
      <PageHeader eyebrow={greet} title={`${user?.full_name.split(" ")[0]}'s farm overview`} subtitle="Your detections, infestation levels and alerts at a glance."
        actions={<Link to="/app/detect" className="btn-primary"><ScanSearch className="h-4 w-4" />Scan crop</Link>} />
      {o.total_scans === 0 ? (
        <Empty title="No scans yet" body="Upload a photo of your crop or a sticky trap to get your first pest analysis." action={<Link to="/app/detect" className="btn-primary">Run your first scan</Link>} icon={<ScanSearch className="h-7 w-7" />} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Total scans" value={o.total_scans} icon={<ScanSearch className="h-4 w-4" />} hint={`${o.scans_with_pests} with pests`} />
            <Stat label="Pests detected" value={o.total_pests.toLocaleString()} icon={<Bug className="h-4 w-4" />} hint={o.most_frequent_pest ? `Most common: ${titleCase(o.most_frequent_pest)}` : undefined} />
            <Stat label="High-risk scans" value={o.high_risk_detections} icon={<ShieldAlert className="h-4 w-4" />} tone={o.high_risk_detections ? "red" : "forest"} hint="High or critical severity" />
            <Stat label="Avg. confidence" value={pct(o.average_confidence, 1)} icon={<Percent className="h-4 w-4" />} tone="amber" hint="Across all detections" />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">Pest activity — last 30 days</h2><Link to="/app/analytics" className="text-sm font-semibold text-forest-700 dark:text-forest-300">Analytics →</Link></div>
              {tr.data?.series.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={tr.data.series}>
                    <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#43814d" stopOpacity={0.35} /><stop offset="100%" stopColor="#43814d" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(27,55,35,.08)" vertical={false} />
                    <XAxis dataKey="period" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} width={32} />
                    <Tooltip {...tooltipStyle} />
                    <Area type="monotone" dataKey="pests" name="Pests" stroke="#31673b" strokeWidth={2} fill="url(#g1)" />
                    <Area type="monotone" dataKey="scans" name="Scans" stroke="#ca8a04" strokeWidth={2} fill="transparent" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <p className="muted py-16 text-center text-sm">No scans in the last 30 days.</p>}
            </Card>
            <Card>
              <h2 className="mb-4 text-lg font-semibold">Severity overview</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={o.severity_distribution} layout="vertical" margin={{ left: 10 }}>
                  <XAxis type="number" hide allowDecimals={false} />
                  <YAxis type="category" dataKey="level" tick={{ fontSize: 12 }} tickFormatter={(l: string) => LEVEL_META[l].label} width={70} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="count" name="Scans" radius={[0, 6, 6, 0]}>{o.severity_distribution.map((s) => <Cell key={s.level} fill={LEVEL_META[s.level].color} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Recent detections</h2><Link to="/app/history" className="text-sm font-semibold text-forest-700 dark:text-forest-300">View all →</Link></div>
              <div className="divide-y divide-forest-900/[.07] dark:divide-white/[.06]">
                {o.recent.map((d) => (
                  <Link key={d.id} to={`/app/detections/${d.id}`} className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-3 hover:bg-forest-50 dark:hover:bg-white/5">
                    <div className="grid h-10 w-10 place-items-center rounded-xl bg-forest-100 text-forest-700 dark:bg-forest-500/15 dark:text-forest-300"><Bug className="h-5 w-5" /></div>
                    <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{d.top_pest ? titleCase(d.top_pest) : "No pests found"}</div><div className="muted text-xs">{fmtDate(d.created_at)} · {d.total_count} detected</div></div>
                    <LevelBadge level={d.severity_level} score={d.severity_score} />
                    <ArrowRight className="h-4 w-4 text-forest-900/30 dark:text-white/30" />
                  </Link>
                ))}
              </div>
            </Card>
            <div className="space-y-6">
              <Card>
                <div className="mb-3 flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-orange-600" /><h2 className="text-lg font-semibold">Density alerts</h2></div>
                {densityAlerts.length ? densityAlerts.map((a) => (
                  <Link key={a.id} to={a.detection_id ? `/app/detections/${a.detection_id}` : "/app/alerts"} className="mb-2 block rounded-xl border border-forest-900/[.07] p-3 hover:bg-forest-50 dark:border-white/10 dark:hover:bg-white/5">
                    <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{a.title}</span><LevelBadge level={a.level} /></div>
                    <div className="muted mt-1 text-xs">{fmtDate(a.created_at)}</div>
                  </Link>
                )) : <p className="muted text-sm">No high or critical infestations recently. 🌱</p>}
              </Card>
              <Card>
                <div className="mb-2 flex items-center justify-between"><div className="flex items-center gap-2"><CloudSun className="h-4 w-4 text-forest-600" /><h2 className="text-lg font-semibold">Weather</h2></div><Link to="/app/weather" className="text-sm font-semibold text-forest-700 dark:text-forest-300">Details →</Link></div>
                {wx.data?.status === "ok" && wx.data.current ? (
                  <div>
                    <div className="font-display text-3xl font-semibold">{Math.round(wx.data.current.temperature_c)}°C</div>
                    <div className="muted text-sm">{wx.data.current.description} · RH {wx.data.current.humidity_pct}% · Rain {wx.data.current.rainfall_mm} mm</div>
                    {wx.data.pest_risk?.[0] && <div className="mt-2 text-sm"><LevelBadge level={wx.data.pest_risk[0].risk === "info" ? "low" : wx.data.pest_risk[0].risk} /> <span className="ml-1">{wx.data.pest_risk[0].title}</span></div>}
                  </div>
                ) : wx.data?.status === "no_location" ? <p className="muted text-sm">Add your farm location in <Link className="underline" to="/app/profile">Settings</Link> to see local weather.</p>
                  : wx.loading ? <p className="muted text-sm">Loading…</p> : <p className="muted text-sm">Live weather is unavailable right now.</p>}
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
