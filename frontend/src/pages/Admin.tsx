import { Activity, Bug, Cpu, Database, ScanSearch, ShieldAlert, Users } from "lucide-react";
import { Fragment } from "react";
import { Link } from "react-router-dom";
import { Card, ErrorBox, LevelBadge, PageHeader, Spinner, Stat } from "../components/ui";
import { api, type ModelInfo } from "../lib/api";
import { fmtDate, pct, titleCase, useApi } from "../lib/hooks";

interface Stats { users: number; active_users: number; detections: number; pests_detected: number; avg_inference_ms: number; top_pests: { pest: string; count: number }[]; severity: Record<string, number>; alerts_open: number; }
interface AUser { id: number; email: string; full_name: string; role: string; is_active: boolean; language: string; created_at: string; detections: number; }
interface AAlert { id: number; user: string; title: string; level: string; detection_id: number | null; is_read: boolean; created_at: string; }

export default function Admin() {
  const stats = useApi<Stats>("/api/admin/stats");
  const users = useApi<AUser[]>("/api/admin/users");
  const alerts = useApi<AAlert[]>("/api/admin/alerts");
  const model = useApi<ModelInfo>("/api/model/info");
  const patch = async (u: AUser, body: Partial<AUser>) => {
    try { await api.patch(`/api/admin/users/${u.id}`, body); users.reload(); } catch (e) { alert((e as Error).message); }
  };
  if (stats.loading) return <Spinner />;
  if (stats.error) return <ErrorBox message={stats.error} />;
  const s = stats.data!;
  const ds = (model.data?.dataset_stats ?? {}) as { images_per_split?: Record<string, number>; cleaning?: Record<string, number>; split_method?: string; licence?: string; source?: string };
  const perClass = Object.entries(model.data?.per_class ?? {}).sort((a, b) => b[1].map50 - a[1].map50);

  return (
    <div>
      <PageHeader eyebrow="Administration" title="Admin dashboard" subtitle="Users, model and dataset information, platform-wide detection statistics and alert monitoring." />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Users" value={s.users} icon={<Users className="h-4 w-4" />} hint={`${s.active_users} active`} />
        <Stat label="Detections" value={s.detections} icon={<ScanSearch className="h-4 w-4" />} hint={`${s.pests_detected} pests found`} />
        <Stat label="Avg inference" value={`${s.avg_inference_ms} ms`} icon={<Activity className="h-4 w-4" />} tone="amber" />
        <Stat label="Open high/critical alerts" value={s.alerts_open} icon={<ShieldAlert className="h-4 w-4" />} tone={s.alerts_open ? "red" : "forest"} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center gap-2"><Cpu className="h-5 w-5 text-forest-600" /><h2 className="text-lg font-semibold">Model</h2></div>
          {model.data?.available ? (
            <>
              <dl className="grid grid-cols-2 gap-y-2 text-sm">
                {[["Name", `${model.data.name} v${model.data.version}`], ["Architecture", model.data.architecture], ["Dataset", model.data.dataset], ["Classes", model.data.num_classes],
                  ["Precision", pct(model.data.metrics.precision as number, 1)], ["Recall", pct(model.data.metrics.recall as number, 1)], ["F1", pct(model.data.metrics.f1 as number, 1)],
                  ["mAP@0.5", pct(model.data.metrics.map50 as number, 1)], ["mAP@0.5:0.95", pct(model.data.metrics.map50_95 as number, 1)],
                  ["Conf. threshold", model.data.thresholds.confidence]].map(([k, v]) => <Fragment key={k as string}><dt className="muted">{k}</dt><dd className="font-semibold">{v as string}</dd></Fragment>)}
              </dl>
              {perClass.length > 0 && (
                <details className="mt-4 text-sm"><summary className="cursor-pointer font-semibold">Per-class test metrics ({perClass.length})</summary>
                  <div className="mt-2 max-h-72 overflow-y-auto"><table className="w-full text-xs"><thead><tr className="muted text-left"><th>Class</th><th>P</th><th>R</th><th>mAP50</th></tr></thead>
                    <tbody>{perClass.map(([c, m]) => <tr key={c} className="border-t border-forest-900/[.07] dark:border-white/10"><td className="py-1">{titleCase(c)}</td><td>{pct(m.precision)}</td><td>{pct(m.recall)}</td><td>{pct(m.map50)}</td></tr>)}</tbody></table></div>
                </details>
              )}
            </>
          ) : <ErrorBox message="No trained model is loaded on the server." />}
        </Card>
        <Card>
          <div className="mb-3 flex items-center gap-2"><Database className="h-5 w-5 text-forest-600" /><h2 className="text-lg font-semibold">Dataset</h2></div>
          {ds.images_per_split ? (
            <div className="space-y-2 text-sm">
              <p><b>{model.data?.dataset}</b> — {Object.entries(ds.images_per_split).map(([k, v]) => `${k}: ${v.toLocaleString()}`).join(" · ")}</p>
              <p className="muted">Split: {ds.split_method}</p>
              {ds.cleaning && <p className="muted">Removed during cleaning: {Object.entries(ds.cleaning).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(", ") || "none"}</p>}
              <p className="muted">Licence: {ds.licence}</p>
              {model.data?.dataset_source && <a className="text-forest-700 underline dark:text-forest-300" href={model.data.dataset_source} target="_blank" rel="noreferrer">Dataset homepage</a>}
            </div>
          ) : <p className="muted text-sm">Dataset statistics will appear once the trained model metadata is deployed.</p>}
          <h3 className="mb-2 mt-5 font-sans text-sm font-semibold">Most detected pests (all users)</h3>
          {s.top_pests.map((p) => <div key={p.pest} className="flex justify-between border-t border-forest-900/[.07] py-1.5 text-sm dark:border-white/10"><span className="flex items-center gap-2"><Bug className="h-3.5 w-3.5 text-forest-600" />{titleCase(p.pest)}</span><span className="font-semibold">{p.count}</span></div>)}
        </Card>
      </div>
      <Card className="mt-6 overflow-x-auto">
        <h2 className="mb-3 text-lg font-semibold">Users</h2>
        <table className="w-full min-w-[640px] text-sm">
          <thead><tr className="muted text-left text-xs uppercase"><th className="pb-2">Name</th><th>Email</th><th>Role</th><th>Scans</th><th>Joined</th><th>Status</th></tr></thead>
          <tbody>{users.data?.map((u) => (
            <tr key={u.id} className="border-t border-forest-900/[.07] dark:border-white/10">
              <td className="py-2 font-semibold">{u.full_name}</td><td>{u.email}</td>
              <td><select className="rounded-lg border border-forest-900/15 bg-transparent px-2 py-1 text-xs dark:border-white/10" value={u.role} onChange={(e) => patch(u, { role: e.target.value })}><option value="farmer">farmer</option><option value="admin">admin</option></select></td>
              <td>{u.detections}</td><td>{fmtDate(u.created_at)}</td>
              <td><button className={u.is_active ? "chip bg-forest-100 text-forest-800" : "chip bg-red-100 text-red-800"} onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? "Active" : "Disabled"}</button></td>
            </tr>))}</tbody>
        </table>
      </Card>
      <Card className="mt-6">
        <h2 className="mb-3 text-lg font-semibold">Alert monitoring (high & critical)</h2>
        {alerts.data?.length ? alerts.data.slice(0, 20).map((a) => (
          <div key={a.id} className="flex items-center gap-3 border-t border-forest-900/[.07] py-2 text-sm dark:border-white/10">
            <LevelBadge level={a.level} /><span className="flex-1 font-semibold">{a.title}</span><span className="muted">{a.user}</span><span className="muted text-xs">{fmtDate(a.created_at)}</span>
            {a.detection_id && <Link className="text-xs font-semibold text-forest-700 dark:text-forest-300" to={`/app/detections/${a.detection_id}`}>Open</Link>}
          </div>)) : <p className="muted text-sm">No high or critical alerts.</p>}
      </Card>
    </div>
  );
}
