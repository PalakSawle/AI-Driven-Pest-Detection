import { KeyRound, LocateFixed, Save, Sprout } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Card, ErrorBox, PageHeader, Spinner, Toggle } from "../components/ui";
import { api, type Crop, type Profile as P } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi, useTheme } from "../lib/hooks";

export default function Profile() {
  const prof = useApi<P>("/api/profile");
  const crops = useApi<Crop[]>("/api/crops");
  const { refresh } = useAuth();
  const { dark, toggle } = useTheme();
  const [params] = useSearchParams();
  const [f, setF] = useState({ full_name: "", phone: "", language: "en", email_alerts: false });
  const [farm, setFarm] = useState({ name: "My farm", location_name: "", state: "", latitude: "", longitude: "", area_hectares: "" });
  const [cropIds, setCropIds] = useState<number[]>([]);
  const [msg, setMsg] = useState<string | null>(null); const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const [pw, setPw] = useState({ current_password: "", new_password: "" }); const [pwMsg, setPwMsg] = useState<string | null>(null);

  useEffect(() => {
    const p = prof.data; if (!p) return;
    setF({ full_name: p.full_name, phone: p.phone ?? "", language: p.language, email_alerts: p.email_alerts });
    setCropIds(p.crops.map((c) => c.id));
    const fm = p.farms[0];
    if (fm) setFarm({ name: fm.name, location_name: fm.location_name ?? "", state: fm.state ?? "", latitude: fm.latitude?.toString() ?? "", longitude: fm.longitude?.toString() ?? "", area_hectares: fm.area_hectares?.toString() ?? "" });
  }, [prof.data]);

  const num = (s: string) => (s.trim() === "" ? null : Number(s));
  const save = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try {
      await api.patch("/api/profile", { ...f, phone: f.phone || null, crop_ids: cropIds,
        farm: { name: farm.name || "My farm", location_name: farm.location_name || null, state: farm.state || null, latitude: num(farm.latitude), longitude: num(farm.longitude), area_hectares: num(farm.area_hectares) } });
      await refresh(); setMsg("Profile saved.");
    } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };
  const locate = () => navigator.geolocation?.getCurrentPosition((p) => setFarm({ ...farm, latitude: p.coords.latitude.toFixed(4), longitude: p.coords.longitude.toFixed(4) }), () => setErr("Location permission denied — enter coordinates manually."));
  const changePw = async () => {
    setPwMsg(null);
    try { await api.post("/api/auth/change-password", pw); setPwMsg("Password changed."); setPw({ current_password: "", new_password: "" }); } catch (e) { setPwMsg((e as Error).message); }
  };

  if (prof.loading) return <Spinner />;
  return (
    <div>
      <PageHeader eyebrow="Account" title="Profile & settings" subtitle="Your details, farm location, crops and preferences." actions={<button className="btn-primary" onClick={save} disabled={busy}><Save className="h-4 w-4" />Save changes</button>} />
      {params.get("welcome") && <div className="mb-4 rounded-2xl bg-forest-100 p-4 text-sm dark:bg-forest-500/15">Welcome to AgriGuard AI! 🌱 Add your farm location and crops so we can tailor weather, severity scoring and advice.</div>}
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      {msg && <div className="mb-4 rounded-xl bg-forest-50 p-3 text-sm font-semibold text-forest-800 dark:bg-white/5 dark:text-forest-200">{msg}</div>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Personal</h2>
          <div className="space-y-3">
            <div><label className="label">Full name</label><input className="input" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></div>
            <div><label className="label">Email</label><input className="input opacity-60" value={prof.data?.email ?? ""} disabled /></div>
            <div><label className="label">Phone</label><input className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></div>
            <div><label className="label">Language (chatbot & labels)</label><select className="input" value={f.language} onChange={(e) => setF({ ...f, language: e.target.value })}><option value="en">English</option><option value="hinglish">Hinglish</option><option value="hi">हिंदी</option></select></div>
            <div className="flex flex-col gap-3 pt-2">
              <Toggle checked={f.email_alerts} onChange={(v) => setF({ ...f, email_alerts: v })} label="Email me high & critical infestation alerts" />
              <Toggle checked={dark} onChange={toggle} label="Dark mode" />
            </div>
          </div>
        </Card>
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Farm location</h2>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Farm name</label><input className="input" value={farm.name} onChange={(e) => setFarm({ ...farm, name: e.target.value })} /></div>
              <div><label className="label">Area (ha)</label><input type="number" min={0} step="0.01" className="input" value={farm.area_hectares} onChange={(e) => setFarm({ ...farm, area_hectares: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Village / district</label><input className="input" value={farm.location_name} onChange={(e) => setFarm({ ...farm, location_name: e.target.value })} /></div>
              <div><label className="label">State</label><input className="input" value={farm.state} onChange={(e) => setFarm({ ...farm, state: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-[1fr_1fr_auto] items-end gap-3">
              <div><label className="label">Latitude</label><input type="number" step="0.0001" className="input" value={farm.latitude} onChange={(e) => setFarm({ ...farm, latitude: e.target.value })} /></div>
              <div><label className="label">Longitude</label><input type="number" step="0.0001" className="input" value={farm.longitude} onChange={(e) => setFarm({ ...farm, longitude: e.target.value })} /></div>
              <button className="btn-outline !px-3" onClick={locate} title="Use my current location" aria-label="Use my current location"><LocateFixed className="h-4 w-4" /></button>
            </div>
            <p className="muted text-xs">Coordinates power local weather and pest-risk hints.</p>
          </div>
        </Card>
        <Card>
          <div className="mb-4 flex items-center gap-2"><Sprout className="h-5 w-5 text-forest-600" /><h2 className="text-lg font-semibold">Crop preferences</h2></div>
          <div className="flex flex-wrap gap-2">
            {crops.data?.map((c) => {
              const on = cropIds.includes(c.id);
              return <button key={c.id} onClick={() => setCropIds(on ? cropIds.filter((x) => x !== c.id) : [...cropIds, c.id])} className={on ? "chip bg-forest-800 py-1.5 text-white" : "chip border border-forest-900/15 py-1.5 dark:border-white/10"}>{c.name} <span className="opacity-60">{c.name_hi}</span></button>;
            })}
          </div>
          <p className="muted mt-3 text-xs">Your first selected crop is pre-filled on the Detect page.</p>
        </Card>
        <Card>
          <div className="mb-4 flex items-center gap-2"><KeyRound className="h-5 w-5 text-forest-600" /><h2 className="text-lg font-semibold">Change password</h2></div>
          <div className="space-y-3">
            <input type="password" className="input" placeholder="Current password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />
            <input type="password" className="input" placeholder="New password (min 8)" minLength={8} value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />
            {pwMsg && <p className="text-sm">{pwMsg}</p>}
            <button className="btn-outline" onClick={changePw} disabled={!pw.current_password || pw.new_password.length < 8}>Update password</button>
          </div>
        </Card>
      </div>
    </div>
  );
}
