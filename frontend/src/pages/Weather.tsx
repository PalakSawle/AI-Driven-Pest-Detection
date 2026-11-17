import { CloudRain, CloudSun, Droplets, LocateFixed, Thermometer, Wind } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Empty, ErrorBox, LevelBadge, PageHeader, Spinner, Stat } from "../components/ui";
import { qs } from "../lib/api";
import { fmtDate, useApi } from "../lib/hooks";
import { tooltipStyle } from "./Dashboard";

interface WeatherResp {
  status: "ok" | "unavailable" | "no_location"; message?: string; provider?: string; latitude?: number; longitude?: number; note?: string;
  current?: { temperature_c: number; humidity_pct: number; rainfall_mm: number; wind_kmh: number; description: string; time?: string };
  daily?: { date: string; t_max: number; t_min: number; rain_mm: number; rh_mean: number | null }[];
  pest_risk?: { risk: string; title: string; detail: string }[];
  last_known?: { fetched_at: string; temperature_c: number; humidity_pct: number; rainfall_mm: number; provider: string } | null;
}

export default function Weather() {
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [geoErr, setGeoErr] = useState<string | null>(null);
  const w = useApi<WeatherResp>(`/api/weather${coords ? qs(coords) : ""}`, [coords]);
  const locate = () => {
    setGeoErr(null);
    if (!navigator.geolocation) return setGeoErr("Location is not supported by this browser.");
    navigator.geolocation.getCurrentPosition((p) => setCoords({ lat: +p.coords.latitude.toFixed(4), lon: +p.coords.longitude.toFixed(4) }),
      () => setGeoErr("Location permission denied. Add your farm location in Settings instead."), { timeout: 10000 });
  };
  const d = w.data;
  return (
    <div>
      <PageHeader eyebrow="Weather & crop monitoring" title="Local weather" subtitle="Live conditions and a 7-day outlook, with weather-based pest-risk hints."
        actions={<button className="btn-outline" onClick={locate}><LocateFixed className="h-4 w-4" />Use my location</button>} />
      {geoErr && <div className="mb-4"><ErrorBox message={geoErr} /></div>}
      {w.loading ? <Spinner /> : w.error ? <ErrorBox message={w.error} onRetry={w.reload} /> : d?.status === "no_location" ? (
        <Empty title="No farm location yet" body="Add your farm's location in Settings, or use your current location." icon={<CloudSun className="h-7 w-7" />}
          action={<div className="flex gap-2"><Link to="/app/profile" className="btn-primary">Add farm location</Link><button className="btn-outline" onClick={locate}>Use my location</button></div>} />
      ) : d?.status === "unavailable" ? (
        <Card>
          <ErrorBox message={`Live weather is unavailable right now (${d.message}). No values are shown rather than guessing.`} onRetry={w.reload} />
          {d.last_known && <p className="muted mt-3 text-sm">Last successful reading ({fmtDate(d.last_known.fetched_at)}, {d.last_known.provider}): {d.last_known.temperature_c}°C, RH {d.last_known.humidity_pct}%, rain {d.last_known.rainfall_mm} mm — this is old data.</p>}
        </Card>
      ) : d?.current && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Temperature" value={`${d.current.temperature_c.toFixed(1)}°C`} icon={<Thermometer className="h-4 w-4" />} hint={d.current.description} />
            <Stat label="Humidity" value={`${d.current.humidity_pct}%`} icon={<Droplets className="h-4 w-4" />} />
            <Stat label="Rainfall (now)" value={`${d.current.rainfall_mm} mm`} icon={<CloudRain className="h-4 w-4" />} />
            <Stat label="Wind" value={`${d.current.wind_kmh} km/h`} icon={<Wind className="h-4 w-4" />} />
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
            <Card>
              <h2 className="mb-4 text-lg font-semibold">7-day outlook</h2>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={d.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(27,55,35,.08)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v: string) => new Date(v).toLocaleDateString(undefined, { weekday: "short" })} />
                  <YAxis yAxisId="t" tick={{ fontSize: 11 }} width={32} unit="°" /><YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11 }} width={36} unit="mm" />
                  <Tooltip {...tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar yAxisId="r" dataKey="rain_mm" name="Rain (mm)" fill="#93c5fd" radius={[6, 6, 0, 0]} />
                  <Line yAxisId="t" dataKey="t_max" name="Max °C" stroke="#ea580c" strokeWidth={2} />
                  <Line yAxisId="t" dataKey="t_min" name="Min °C" stroke="#2563eb" strokeWidth={2} />
                </ComposedChart>
              </ResponsiveContainer>
            </Card>
            <Card>
              <h2 className="mb-4 text-lg font-semibold">Weather-based pest risk</h2>
              <div className="space-y-3">{d.pest_risk?.map((r) => (
                <div key={r.title} className="rounded-xl border border-forest-900/[.07] p-3 dark:border-white/10">
                  <div className="flex items-center justify-between gap-2"><span className="font-semibold">{r.title}</span>{r.risk !== "info" ? <LevelBadge level={r.risk} /> : <span className="chip bg-sky-100 text-sky-800 dark:bg-sky-500/15 dark:text-sky-200">Spray timing</span>}</div>
                  <p className="muted mt-1 text-sm">{r.detail}</p>
                </div>))}</div>
              <p className="muted mt-4 text-xs">{d.note} Source: {d.provider} · {d.latitude?.toFixed(3)}, {d.longitude?.toFixed(3)}</p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
