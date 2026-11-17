import { ArrowLeft, Download, Info, Sprout, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import TreatmentDetail from "../components/TreatmentDetail";
import { Card, ConfidenceBar, DetectionImage, ErrorBox, LevelBadge, PageHeader, SeverityMeter, Spinner, Toggle } from "../components/ui";
import { api, type Detection, type Threshold, type Treatment, type Trends } from "../lib/api";
import { fmtDate, fmtDay, pct, titleCase, useApi } from "../lib/hooks";
import { tooltipStyle } from "./Dashboard";

const COLORS = ["#31673b", "#ea580c", "#2563eb", "#ca8a04", "#7c3aed", "#db2777"];

export default function DetectionReport() {
  const { id } = useParams();
  const nav = useNavigate();
  const det = useApi<Detection>(`/api/detections/${id}`, [id]);
  const trends = useApi<Trends>("/api/analytics/trends?period=daily&days=90");
  const thresholds = useApi<Threshold[]>("/api/alerts/thresholds");
  const [showBoxes, setShowBoxes] = useState(true);
  const [tab, setTab] = useState(0);
  const pests = det.data ? Object.keys(det.data.class_counts) : [];
  const tr = useApi<Treatment>(pests[tab] ? `/api/treatments/${encodeURIComponent(pests[tab])}` : null, [pests[tab]]);

  if (det.loading) return <Spinner />;
  if (det.error) return <ErrorBox message={det.error} onRetry={det.reload} />;
  const d = det.data!;

  // population graph: density history for the pests in this detection
  const hist = (trends.data?.density ?? []).filter((x) => pests.includes(x.pest) && x.unit === d.densities[0]?.unit);
  const byDate: Record<string, Record<string, number | string>> = {};
  hist.forEach((x) => { const k = x.date; byDate[k] = { ...(byDate[k] ?? { date: fmtDay(x.date) }), [x.pest]: x.value }; });
  const series = Object.keys(byDate).sort().map((k) => byDate[k]);
  const thr = (p: string) => thresholds.data?.find((t) => t.pest_class === p && t.user_id) ?? thresholds.data?.find((t) => t.pest_class === p) ?? thresholds.data?.find((t) => t.pest_class === "*");

  const remove = async () => {
    if (!confirm("Delete this detection and its images permanently?")) return;
    await api.del(`/api/detections/${d.id}`); nav("/app/history");
  };

  return (
    <div>
      <Link to="/app/history" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-forest-700 dark:text-forest-300"><ArrowLeft className="h-4 w-4" />History</Link>
      <PageHeader eyebrow={`Pest analysis · Report #${d.id}`} title={d.top_pest ? titleCase(d.top_pest) + (pests.length > 1 ? ` + ${pests.length - 1} more` : "") : "No pests detected"}
        subtitle={`${fmtDate(d.created_at)} · ${d.crop_name ?? "Crop not specified"}${d.growth_stage ? ` · ${titleCase(d.growth_stage)}` : ""} · ${d.sample_type.replace("_", " ")}`}
        actions={<>
          <button className="btn-outline" onClick={() => api.download(`/api/detections/${d.id}/report.pdf`, `agriguard_report_${d.id}.pdf`)}><Download className="h-4 w-4" />PDF report</button>
          <button className="btn-ghost text-red-700 dark:text-red-300" onClick={remove}><Trash2 className="h-4 w-4" />Delete</button>
        </>} />
      {d.warnings.map((w) => <div key={w} className="mb-3 flex gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200"><Info className="mt-0.5 h-4 w-4 shrink-0" />{w}</div>)}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Annotated image</h2><Toggle checked={showBoxes} onChange={setShowBoxes} label="Boxes" /></div>
          <DetectionImage src={d.image_url} width={d.image_width} height={d.image_height} instances={d.instances} showBoxes={showBoxes} />
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            {[["Pests", d.total_count], ["Species", pests.length], ["Mean conf.", pct(d.mean_confidence, 1)], ["Inference", `${d.inference_ms.toFixed(0)} ms`]].map(([k, v]) => (
              <div key={k as string} className="rounded-xl bg-forest-50 p-3 dark:bg-white/5"><div className="muted text-xs">{k}</div><div className="font-semibold">{v}</div></div>))}
          </div>
        </Card>
        <Card>
          <h2 className="mb-2 text-lg font-semibold">Infestation severity</h2>
          {d.severity && <>
            <SeverityMeter score={d.severity.score} level={d.severity.level} />
            <p className="mt-4 text-sm">{d.severity.explanation}</p>
            <div className="mt-4 rounded-xl bg-forest-50 p-3 text-sm dark:bg-white/5"><span className="font-semibold">Recommended next action: </span>{d.severity.recommended_action}</div>
            <details className="mt-4 text-sm">
              <summary className="cursor-pointer font-semibold">How this score was calculated</summary>
              <table className="mt-2 w-full text-left text-xs"><tbody>
                {d.severity.factors.map((f) => <tr key={f.name} className="border-t border-forest-900/[.07] dark:border-white/10"><td className="py-1.5 pr-2 font-semibold">{f.name}</td><td className="py-1.5 pr-2 tabular-nums">{f.value}</td><td className="muted py-1.5">{f.effect}</td></tr>)}
              </tbody></table>
              <p className="muted mt-2 text-xs">A transparent, configurable rule-based index to prioritise action — not a scientifically validated yield-loss prediction.</p>
            </details>
          </>}
        </Card>
      </div>

      {pests.length > 0 && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="mb-1 text-lg font-semibold">Pest density</h2>
            <p className="muted mb-4 text-xs">{d.densities[0]?.method === "trap_rate" ? "Trap-catch rate normalised by trap area and time in field." : "Estimated image-based count (relative infestation index) — not pests per m²."}</p>
            <div className="space-y-3">
              {d.densities.map((x) => {
                const t = thr(x.pest_class); const max = t ? t.critical : Math.max(x.value, 1);
                const confs = d.instances.filter((i) => i.pest_class === x.pest_class).map((i) => i.confidence);
                return (
                  <div key={x.pest_class} className="rounded-xl border border-forest-900/[.07] p-3 dark:border-white/10">
                    <div className="flex items-center justify-between"><Link className="font-semibold hover:underline" to={`/app/treatments/${encodeURIComponent(x.pest_class)}`}>{titleCase(x.pest_class)}</Link><LevelBadge level={x.level} /></div>
                    <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-gradient-to-r from-lime-200 via-yellow-200 via-60% to-red-200 dark:opacity-80">
                      <div className="h-full rounded-full bg-forest-900/70 dark:bg-white/70" style={{ width: `${Math.min(100, (x.value / max) * 100)}%` }} />
                    </div>
                    <div className="muted mt-1.5 flex justify-between text-xs"><span>{x.count} detected · {x.value} {x.unit}</span>{t && <span>critical at {t.critical}</span>}</div>
                    <div className="mt-2"><ConfidenceBar value={confs.reduce((a, b) => a + b, 0) / confs.length} /></div>
                  </div>
                );
              })}
            </div>
            <Link to="/app/alerts?tab=thresholds" className="mt-3 inline-block text-xs font-semibold text-forest-700 dark:text-forest-300">Configure alert thresholds →</Link>
          </Card>
          <Card>
            <h2 className="mb-1 text-lg font-semibold">Population trend (90 days)</h2>
            <p className="muted mb-4 text-xs">Density of these pests across your scans.</p>
            {series.length > 1 ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={series}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(27,55,35,.08)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} width={32} /><Tooltip {...tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} />
                  {pests.slice(0, 6).map((p, i) => <Line key={p} dataKey={p} name={titleCase(p)} stroke={COLORS[i]} strokeWidth={2} dot={{ r: 3 }} connectNulls />)}
                  {pests.length === 1 && thr(pests[0]) && <ReferenceLine y={thr(pests[0])!.high} stroke="#ea580c" strokeDasharray="4 4" label={{ value: "high", fontSize: 10, fill: "#ea580c" }} />}
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="muted py-16 text-center text-sm">Scan the same field again over the coming days to see a trend.</p>}
          </Card>
        </div>
      )}

      {pests.length > 0 && (
        <Card className="mt-6">
          <div className="mb-4 flex items-center gap-2"><Sprout className="h-5 w-5 text-forest-600" /><h2 className="text-lg font-semibold">Crop impact & treatment</h2></div>
          {d.crop_name ? <p className="mb-4 text-sm">Crop: <b>{d.crop_name}</b>{d.growth_stage && <> at <b>{d.growth_stage}</b> stage</>}. Sensitive stages (e.g. flowering) raise the severity score.</p>
            : <p className="muted mb-4 text-sm">Tip: select your crop and growth stage when scanning for crop-specific scoring.</p>}
          <div className="mb-5 flex flex-wrap gap-2">
            {pests.map((p, i) => <button key={p} onClick={() => setTab(i)} className={i === tab ? "btn-primary !py-1.5" : "btn-outline !py-1.5"}>{titleCase(p)}</button>)}
          </div>
          {tr.loading ? <Spinner /> : tr.error ? <ErrorBox message={tr.error} /> : tr.data && <TreatmentDetail t={tr.data} crop={d.crop_name} />}
        </Card>
      )}
    </div>
  );
}
