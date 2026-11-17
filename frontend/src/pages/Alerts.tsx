import clsx from "clsx";
import { Bell, BellOff, CalendarClock, CheckCheck, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, Empty, ErrorBox, LevelBadge, PageHeader, Spinner } from "../components/ui";
import { api, type Notification, type Threshold } from "../lib/api";
import { fmtDate, titleCase, useApi } from "../lib/hooks";

export default function Alerts() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "alerts";
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [scheduled, setScheduled] = useState(false);
  const list = useApi<Notification[]>(`/api/alerts?unread_only=${unreadOnly}&include_scheduled=${scheduled}`);
  const refresh = () => { list.reload(); window.dispatchEvent(new Event("agriguard:alerts")); };
  const toggle = async (n: Notification) => { await api.patch(`/api/alerts/${n.id}/read?read=${!n.is_read}`); refresh(); };
  const del = async (n: Notification) => { await api.del(`/api/alerts/${n.id}`); refresh(); };
  const now = Date.now();

  return (
    <div>
      <PageHeader eyebrow="Smart alerts" title="Notifications & alerts" subtitle="Infestation alerts, new detections and treatment follow-up reminders."
        actions={tab === "alerts" && <button className="btn-outline" onClick={async () => { await api.post("/api/alerts/read-all"); refresh(); }}><CheckCheck className="h-4 w-4" />Mark all read</button>} />
      <div className="mb-5 inline-flex rounded-xl bg-forest-100 p-1 dark:bg-white/5">
        {[["alerts", "Alerts"], ["thresholds", "Alert thresholds"]].map(([k, l]) => (
          <button key={k} onClick={() => setParams(k === "alerts" ? {} : { tab: k })} className={clsx("rounded-lg px-4 py-1.5 text-sm font-semibold", tab === k ? "bg-white shadow-soft dark:bg-forest-500/20" : "text-forest-900/60 dark:text-forest-100/60")}>{l}</button>))}
      </div>
      {tab === "thresholds" ? <Thresholds /> : (
        <>
          <div className="mb-4 flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} className="accent-forest-700" />Unread only</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={scheduled} onChange={(e) => setScheduled(e.target.checked)} className="accent-forest-700" />Show upcoming reminders</label>
          </div>
          {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} /> : !list.data?.length ? (
            <Empty title="You're all caught up" body="Alerts appear here after scans, when infestations get high, and as follow-up reminders." icon={<BellOff className="h-7 w-7" />} />
          ) : (
            <div className="space-y-2">
              {list.data.map((n) => {
                const upcoming = n.due_at && new Date(n.due_at.endsWith("Z") ? n.due_at : n.due_at + "Z").getTime() > now;
                return (
                  <Card key={n.id} className={clsx("flex items-start gap-3 !p-4", !n.is_read && "border-l-4 !border-l-forest-600")}>
                    <div className={clsx("grid h-9 w-9 shrink-0 place-items-center rounded-xl", n.level === "critical" ? "bg-red-100 text-red-700" : n.level === "high" ? "bg-orange-100 text-orange-700" : "bg-forest-100 text-forest-700 dark:bg-white/10 dark:text-forest-200")}>
                      {n.type === "follow_up" ? <CalendarClock className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2"><span className={clsx("text-sm", !n.is_read ? "font-bold" : "font-semibold")}>{n.title}</span>{(n.level === "high" || n.level === "critical") && <LevelBadge level={n.level} />}{upcoming && <span className="chip bg-sky-100 text-sky-800">Due {fmtDate(n.due_at!)}</span>}</div>
                      <p className="muted mt-0.5 text-sm">{n.message}</p>
                      <div className="muted mt-1 flex gap-3 text-xs"><span>{fmtDate(n.created_at)}</span>{n.detection_id && <Link className="font-semibold text-forest-700 dark:text-forest-300" to={`/app/detections/${n.detection_id}`}>View detection</Link>}</div>
                    </div>
                    <button className="btn-ghost !p-2 text-xs" onClick={() => toggle(n)}>{n.is_read ? "Mark unread" : "Mark read"}</button>
                    <button className="btn-ghost !p-2" onClick={() => del(n)} aria-label="Delete alert"><Trash2 className="h-4 w-4 text-red-600" /></button>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Thresholds() {
  const th = useApi<Threshold[]>("/api/alerts/thresholds");
  const pests = useApi<{ pests: string[] }>("/api/analytics/filters");
  const [form, setForm] = useState({ pest_class: "*", low: 1, moderate: 3, high: 6, critical: 10 });
  const [err, setErr] = useState<string | null>(null); const [ok, setOk] = useState(false);
  const save = async () => {
    setErr(null); setOk(false);
    try { await api.put("/api/alerts/thresholds", form); setOk(true); th.reload(); } catch (e) { setErr((e as Error).message); }
  };
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
      <Card>
        <h2 className="text-lg font-semibold">Set a pest-specific threshold</h2>
        <p className="muted mt-1 text-sm">Counts are pests detected per image. They are starting points — adjust to local economic thresholds advised by your KVK.</p>
        <div className="mt-4 space-y-3">
          <div><label className="label">Pest</label><select className="input" value={form.pest_class} onChange={(e) => setForm({ ...form, pest_class: e.target.value })}><option value="*">Any pest (default)</option>{pests.data?.pests.map((p) => <option key={p} value={p}>{titleCase(p)}</option>)}</select></div>
          <div className="grid grid-cols-4 gap-2">
            {(["low", "moderate", "high", "critical"] as const).map((k) => <div key={k}><label className="label">{k}</label><input type="number" min={0} step="0.5" className="input" value={form[k]} onChange={(e) => setForm({ ...form, [k]: +e.target.value })} /></div>)}
          </div>
          {err && <ErrorBox message={err} />}
          {ok && <p className="text-sm font-semibold text-forest-700">Saved.</p>}
          <button className="btn-primary" onClick={save}><Save className="h-4 w-4" />Save threshold</button>
        </div>
      </Card>
      <Card>
        <h2 className="mb-3 text-lg font-semibold">Active thresholds</h2>
        {th.loading ? <Spinner /> : (
          <table className="w-full text-sm">
            <thead><tr className="muted text-left text-xs uppercase"><th className="pb-2">Pest</th><th>Low</th><th>Mod.</th><th>High</th><th>Critical</th><th /></tr></thead>
            <tbody>{th.data?.map((t) => (
              <tr key={t.id} className="border-t border-forest-900/[.07] dark:border-white/10">
                <td className="py-2 font-semibold">{t.pest_class === "*" ? "Any pest" : titleCase(t.pest_class)} <span className="muted text-xs font-normal">{t.user_id ? "yours" : "default"}</span></td>
                <td>{t.low}</td><td>{t.moderate}</td><td>{t.high}</td><td>{t.critical}</td>
                <td>{t.user_id && <button className="btn-ghost !p-1.5" onClick={async () => { await api.del(`/api/alerts/thresholds/${t.id}`); th.reload(); }} aria-label="Remove custom threshold"><Trash2 className="h-3.5 w-3.5 text-red-600" /></button>}</td>
              </tr>))}</tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
