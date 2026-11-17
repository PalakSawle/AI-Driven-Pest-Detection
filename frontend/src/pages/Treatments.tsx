import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import TreatmentDetail from "../components/TreatmentDetail";
import { Card, Empty, ErrorBox, PageHeader, Spinner } from "../components/ui";
import type { Treatment } from "../lib/api";
import { titleCase, useApi } from "../lib/hooks";

export default function Treatments() {
  const { pest } = useParams();
  const list = useApi<Treatment[]>("/api/treatments");
  const one = useApi<Treatment>(pest ? `/api/treatments/${encodeURIComponent(pest)}` : null, [pest]);
  const [q, setQ] = useState("");
  const [crop, setCrop] = useState("");
  const crops = useMemo(() => [...new Set((list.data ?? []).flatMap((t) => t.crops))].sort(), [list.data]);
  const filtered = (list.data ?? []).filter((t) =>
    (!q || `${t.common_name} ${t.common_name_hi ?? ""} ${t.scientific_name ?? ""} ${t.pest_key}`.toLowerCase().includes(q.toLowerCase())) &&
    (!crop || t.crops.includes(crop)));

  return (
    <div>
      <PageHeader eyebrow="Smart treatment engine" title="Treatment recommendations" subtitle="Integrated Pest Management guidance — organic, biological and preventive first. Chemical guidance is limited to registered classes; always follow the product label." />
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit lg:sticky lg:top-24">
          <div className="relative"><Search className="absolute left-3 top-3 h-4 w-4 text-forest-900/40" /><input className="input pl-9" placeholder="Search pest (English / हिंदी)" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <select className="input mt-2" value={crop} onChange={(e) => setCrop(e.target.value)}><option value="">All crops</option>{crops.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</select>
          <div className="mt-3 max-h-[60vh] space-y-1 overflow-y-auto pr-1">
            {list.loading ? <Spinner /> : filtered.map((t) => (
              <Link key={t.pest_key} to={`/app/treatments/${encodeURIComponent(t.pest_key)}`} className={`block rounded-xl px-3 py-2 text-sm ${pest === t.pest_key ? "bg-forest-800 text-white" : "hover:bg-forest-50 dark:hover:bg-white/5"}`}>
                <div className="font-semibold">{t.common_name}</div><div className="truncate text-xs opacity-70">{t.scientific_name} · {t.crops.join(", ")}</div>
              </Link>
            ))}
            {!list.loading && !filtered.length && <p className="muted p-3 text-sm">No match.</p>}
          </div>
        </Card>
        <Card>
          {!pest ? <Empty title="Choose a pest" body="Select a pest from the list, or open a detection report to see treatment for the pests found in your field." />
            : one.loading ? <Spinner /> : one.error ? <ErrorBox message={one.error} /> : one.data && <TreatmentDetail t={one.data} />}
        </Card>
      </div>
    </div>
  );
}
