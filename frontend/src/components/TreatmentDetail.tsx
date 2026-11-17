import { AlertTriangle, BookOpen, Bug, FlaskConical, HardHat, Leaf, ShieldCheck, Sprout, Telescope } from "lucide-react";
import type { ReactNode } from "react";
import type { Treatment } from "../lib/api";
import { titleCase } from "../lib/hooks";

function Section({ icon, title, items, tone = "forest" }: { icon: ReactNode; title: string; items: string[]; tone?: "forest" | "amber" }) {
  if (!items.length) return null;
  return (
    <div className="rounded-2xl border border-forest-900/[.07] p-4 dark:border-white/10">
      <div className={`mb-2 flex items-center gap-2 text-sm font-semibold ${tone === "amber" ? "text-amber-700 dark:text-amber-300" : "text-forest-700 dark:text-forest-300"}`}>{icon}{title}</div>
      <ul className="space-y-1.5 text-sm">{items.map((i) => <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-current opacity-50" />{i}</li>)}</ul>
    </div>
  );
}

export default function TreatmentDetail({ t, crop }: { t: Treatment; crop?: string | null }) {
  const cropMismatch = crop && t.crops.length && !t.crops.some((c) => crop.toLowerCase().includes(c.toLowerCase()) || c.toLowerCase().includes(crop.toLowerCase().split(" ")[0]));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-2xl font-semibold">{t.common_name}{t.common_name_hi && <span className="ml-2 font-sans text-base font-normal text-forest-900/50 dark:text-white/50">{t.common_name_hi}</span>}</h3>
          <div className="muted text-sm italic">{t.scientific_name ?? titleCase(t.pest_key)}</div>
          <div className="mt-2 flex flex-wrap gap-1.5">{t.crops.map((c) => <span key={c} className="chip bg-forest-100 text-forest-800 dark:bg-white/10 dark:text-forest-100"><Sprout className="h-3 w-3" />{titleCase(c)}</span>)}</div>
        </div>
        {!t.curated && <span className="chip bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200">General guidance — not species-specific</span>}
      </div>
      {(t.expert_advice_required || cropMismatch) && (
        <div className="flex gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>{t.expert_advice_required && "Expert advice required: confirm the identification and treatment with your local KVK / agriculture officer. "}
            {cropMismatch && `This entry is written for ${t.crops.join(", ")}; you selected ${crop}. Check with an expert before applying it.`}</div>
        </div>
      )}
      <Section icon={<Bug className="h-4 w-4" />} title="Symptoms" items={t.symptoms} />
      <div className="grid gap-4 md:grid-cols-2">
        <Section icon={<Leaf className="h-4 w-4" />} title="Organic options" items={t.organic} />
        <Section icon={<Sprout className="h-4 w-4" />} title="Biological control" items={t.biological} />
        <Section icon={<ShieldCheck className="h-4 w-4" />} title="Prevention" items={t.preventive} />
        <Section icon={<Telescope className="h-4 w-4" />} title="IPM approach" items={t.ipm} />
      </div>
      <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4 dark:border-amber-500/20 dark:bg-amber-500/5">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-800 dark:text-amber-300"><FlaskConical className="h-4 w-4" />Chemical guidance (classes only — last resort)</div>
        <ul className="space-y-2 text-sm">{t.chemical_categories.map((c) => <li key={c.class}><span className="font-semibold">{c.class}</span><span className="muted"> — {c.note}</span></li>)}</ul>
        <p className="mt-3 text-xs text-amber-900/80 dark:text-amber-200/80">AgriGuard never suggests brands or doses. Use only a product registered by CIB&RC for this crop and pest, and follow its label exactly.</p>
      </div>
      <Section icon={<HardHat className="h-4 w-4" />} title="Safety precautions & PPE" items={t.safety} tone="amber" />
      <div className="rounded-2xl bg-forest-50 p-4 text-sm dark:bg-white/5">
        <div className="font-semibold">Follow-up monitoring</div><p className="mt-1">{t.monitoring}</p>
        {t.etl_note && <p className="muted mt-2 text-xs">{t.etl_note}</p>}
      </div>
      <div>
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold"><BookOpen className="h-4 w-4" />References</div>
        <ul className="space-y-1 text-sm">{t.references.map((r) => <li key={r.url + r.title}><a href={r.url} target="_blank" rel="noreferrer" className="text-forest-700 underline-offset-2 hover:underline dark:text-forest-300">{r.title}</a></li>)}</ul>
      </div>
    </div>
  );
}
