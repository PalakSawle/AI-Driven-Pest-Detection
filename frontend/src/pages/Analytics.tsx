import { BarChart3, Cpu } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Empty, ErrorBox, LEVEL_META, PageHeader, Spinner } from "../components/ui";
import { qs, type Crop, type ModelInfo, type Overview, type Trends } from "../lib/api";
import { pct, titleCase, useApi } from "../lib/hooks";
import { tooltipStyle } from "./Dashboard";

const PALETTE = ["#31673b", "#649f6d", "#97c09c", "#ca8a04", "#ea580c", "#2563eb", "#7c3aed", "#db2777", "#0891b2", "#65a30d", "#a16207", "#475569"];

export default function Analytics() {
  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">("daily");
  const [days, setDays] = useState(90);
  const [pest, setPest] = useState(""); const [cropId, setCropId] = useState("");
  const f = { pest, crop_id: cropId };
  const ov = useApi<Overview>(`/api/analytics/overview${qs(f)}`);
  const tr = useApi<Trends>(`/api/analytics/trends${qs({ ...f, period, days })}`);
  const opts = useApi<{ pests: string[] }>("/api/analytics/filters");
  const crops = useApi<Crop[]>("/api/crops");
  const model = useApi<ModelInfo>("/api/model/info");

  return (
    <div>
      <PageHeader eyebrow="Insights" title="Analytics" subtitle="All charts are computed from your saved detection records." />
      <Card className="mb-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div><label className="label">Granularity</label><select className="input" value={period} onChange={(e) => setPeriod(e.target.value as typeof period)}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></div>
          <div><label className="label">Range</label><select className="input" value={days} onChange={(e) => setDays(+e.target.value)}>{[7, 30, 90, 180, 365].map((d) => <option key={d} value={d}>Last {d} days</option>)}</select></div>
          <div><label className="label">Pest</label><select className="input" value={pest} onChange={(e) => setPest(e.target.value)}><option value="">All pests</option>{opts.data?.pests.map((p) => <option key={p} value={p}>{titleCase(p)}</option>)}</select></div>
          <div><label className="label">Crop</label><select className="input" value={cropId} onChange={(e) => setCropId(e.target.value)}><option value="">All crops</option>{crops.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
        </div>
      </Card>
      {ov.loading || tr.loading ? <Spinner /> : ov.error ? <ErrorBox message={ov.error} /> : !ov.data?.total_scans ? (
        <Empty title="No data for these filters" body="Analytics appear once you have scans matching the filters." icon={<BarChart3 className="h-7 w-7" />} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="lg:col-span-2">
            <h2 className="mb-4 text-lg font-semibold">Pest trend</h2>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={tr.data?.series ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(27,55,35,.08)" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} /><YAxis yAxisId="l" tick={{ fontSize: 11 }} width={34} allowDecimals={false} /><YAxis yAxisId="r" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} width={34} />
                <Tooltip {...tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar yAxisId="l" dataKey="pests" name="Pests detected" fill="#649f6d" radius={[6, 6, 0, 0]} />
                <Bar yAxisId="l" dataKey="high_risk" name="High-risk scans" fill="#ea580c" radius={[6, 6, 0, 0]} />
                <Line yAxisId="r" dataKey="avg_severity" name="Avg severity (0–100)" stroke="#1b3723" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </Card>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Pest-wise distribution</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={ov.data.pest_distribution} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} /><YAxis type="category" dataKey="pest" width={130} tick={{ fontSize: 11 }} tickFormatter={(v: string) => titleCase(v).slice(0, 20)} />
                <Tooltip {...tooltipStyle} /><Bar dataKey="count" name="Detections" radius={[0, 6, 6, 0]}>{ov.data.pest_distribution.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Severity distribution</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={ov.data.severity_distribution.filter((s) => s.count)} dataKey="count" nameKey="level" innerRadius={60} outerRadius={100} paddingAngle={2} label={({ level, count }) => `${LEVEL_META[level].label} ${count}`}>
                  {ov.data.severity_distribution.filter((s) => s.count).map((s) => <Cell key={s.level} fill={LEVEL_META[s.level].color} />)}
                </Pie><Tooltip {...tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Crop-wise infestation</h2>
            <div className="overflow-x-auto"><table className="w-full text-sm">
              <thead><tr className="muted text-left text-xs uppercase"><th className="pb-2">Crop</th><th className="pb-2 text-right">Scans</th><th className="pb-2 text-right">Pests</th><th className="pb-2 text-right">Pests/scan</th><th className="pb-2 text-right">High-risk</th></tr></thead>
              <tbody>{ov.data.crop_stats.map((c) => <tr key={c.crop} className="border-t border-forest-900/[.07] dark:border-white/10"><td className="py-2 font-semibold">{c.crop}</td><td className="text-right">{c.scans}</td><td className="text-right">{c.pests}</td><td className="text-right">{(c.pests / c.scans).toFixed(1)}</td><td className="text-right">{c.high_risk}</td></tr>)}</tbody>
            </table></div>
          </Card>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Detection confidence trend</h2>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={(tr.data?.series ?? []).filter((s) => s.avg_confidence != null)}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(27,55,35,.08)" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11 }} width={40} />
                <Tooltip {...tooltipStyle} formatter={(v: number) => pct(v, 1)} /><Line dataKey="avg_confidence" name="Avg confidence" stroke="#2563eb" strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
      {model.data?.available && (
        <Card className="mt-6">
          <div className="mb-4 flex items-center gap-2"><Cpu className="h-5 w-5 text-forest-600" /><h2 className="text-lg font-semibold">Model performance</h2></div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {[["Precision", "precision"], ["Recall", "recall"], ["F1-score", "f1"], ["mAP@0.5", "map50"], ["mAP@0.5:0.95", "map50_95"]].map(([l, k]) => (
              <div key={k} className="rounded-xl bg-forest-50 p-3 dark:bg-white/5"><div className="muted text-xs">{l}</div><div className="font-display text-2xl font-semibold">{typeof model.data!.metrics[k] === "number" ? pct(model.data!.metrics[k] as number, 1) : "—"}</div></div>))}
          </div>
          <p className="muted mt-3 text-xs">{model.data.name} v{model.data.version} · {model.data.architecture} · {model.data.dataset} · {model.data.num_classes} classes · evaluated on the held-out test split.</p>
        </Card>
      )}
    </div>
  );
}
