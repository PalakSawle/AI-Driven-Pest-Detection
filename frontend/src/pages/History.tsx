import { ChevronLeft, ChevronRight, Download, FileText, Filter, History as HistoryIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, Empty, ErrorBox, LevelBadge, PageHeader, Spinner } from "../components/ui";
import { api, fileUrl, qs, type Crop, type Paginated } from "../lib/api";
import { fmtDate, pct, titleCase, useApi } from "../lib/hooks";

export default function History() {
  const [f, setF] = useState({ start: "", end: "", pest: "", crop_id: "", severity: "" });
  const [page, setPage] = useState(1);
  const params = { start: f.start ? `${f.start}T00:00:00` : "", end: f.end ? `${f.end}T23:59:59` : "", pest: f.pest, crop_id: f.crop_id, severity: f.severity };
  const list = useApi<Paginated>(`/api/detections/history${qs({ ...params, page, page_size: 12 })}`);
  const opts = useApi<{ pests: string[]; crops: [number, string][] }>("/api/analytics/filters");
  const crops = useApi<Crop[]>("/api/crops");
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => { setF({ ...f, [k]: e.target.value }); setPage(1); };
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;

  return (
    <div>
      <PageHeader eyebrow="Records" title="Detection history" subtitle="Every scan you've run, with filters and exports."
        actions={<button className="btn-outline" onClick={() => api.download(`/api/detections/export.csv${qs(params)}`, "agriguard_detections.csv")}><Download className="h-4 w-4" />Export CSV</button>} />
      <Card className="mb-6">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Filter className="h-4 w-4" />Filters</div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div><label className="label">From</label><input type="date" className="input" value={f.start} onChange={set("start")} /></div>
          <div><label className="label">To</label><input type="date" className="input" value={f.end} onChange={set("end")} /></div>
          <div><label className="label">Pest</label><select className="input" value={f.pest} onChange={set("pest")}><option value="">All pests</option>{opts.data?.pests.map((p) => <option key={p} value={p}>{titleCase(p)}</option>)}</select></div>
          <div><label className="label">Crop</label><select className="input" value={f.crop_id} onChange={set("crop_id")}><option value="">All crops</option>{crops.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
          <div><label className="label">Severity</label><select className="input" value={f.severity} onChange={set("severity")}><option value="">Any</option>{["safe", "low", "moderate", "high", "critical"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</select></div>
        </div>
      </Card>
      {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : !list.data?.items.length ? (
        <Empty title="No detections found" body="Try clearing filters, or run a new scan." icon={<HistoryIcon className="h-7 w-7" />} action={<Link to="/app/detect" className="btn-primary">New scan</Link>} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {list.data.items.map((d) => (
              <Card key={d.id} className="!p-0 overflow-hidden">
                <Link to={`/app/detections/${d.id}`} className="block">
                  <div className="aspect-[16/10] overflow-hidden bg-forest-950"><img src={fileUrl(d.annotated_url ?? d.image_url)} alt={`Detection ${d.id}`} loading="lazy" className="h-full w-full object-cover transition hover:scale-[1.03]" /></div>
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2"><div className="font-semibold">{d.top_pest ? titleCase(d.top_pest) : "No pests"}</div><LevelBadge level={d.severity_level} score={d.severity_score} /></div>
                    <div className="muted mt-1 text-xs">{fmtDate(d.created_at)} · {d.crop_name ?? "No crop"} · {d.total_count} pests · conf {pct(d.mean_confidence)}</div>
                  </div>
                </Link>
                <div className="flex border-t border-forest-900/[.07] dark:border-white/10">
                  <Link to={`/app/detections/${d.id}`} className="flex-1 py-2.5 text-center text-xs font-semibold hover:bg-forest-50 dark:hover:bg-white/5">View report</Link>
                  <button onClick={() => api.download(`/api/detections/${d.id}/report.pdf`, `agriguard_report_${d.id}.pdf`)} className="flex flex-1 items-center justify-center gap-1 border-l border-forest-900/[.07] py-2.5 text-xs font-semibold hover:bg-forest-50 dark:border-white/10 dark:hover:bg-white/5"><FileText className="h-3.5 w-3.5" />PDF</button>
                </div>
              </Card>
            ))}
          </div>
          <div className="mt-6 flex items-center justify-between text-sm">
            <span className="muted">{list.data.total} detections</span>
            <div className="flex items-center gap-2">
              <button className="btn-outline !p-2" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></button>
              <span>Page {page} of {pages}</span>
              <button className="btn-outline !p-2" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Next page"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
