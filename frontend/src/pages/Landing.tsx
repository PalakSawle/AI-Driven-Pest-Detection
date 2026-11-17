import { motion } from "framer-motion";
import { ArrowRight, BellRing, Bot, Camera, CloudSun, Cpu, Gauge, Languages, Leaf, LineChart, ScanSearch, ShieldCheck, Sprout } from "lucide-react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Layout";
import type { ModelInfo } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";

const fade = { initial: { opacity: 0, y: 16 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true }, transition: { duration: 0.5 } };

export default function Landing() {
  const { user } = useAuth();
  const { data: model } = useApi<ModelInfo>("/api/model/info");
  const m = model?.metrics ?? {};
  const ds = (model?.dataset_stats ?? {}) as { images_per_split?: Record<string, number> };
  const totalImages = ds.images_per_split ? Object.values(ds.images_per_split).reduce((a, b) => a + b, 0) : null;

  return (
    <div className="bg-cream-50 text-forest-950">
      {/* nav */}
      <header className="absolute inset-x-0 top-0 z-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5">
          <Logo light />
          <nav className="hidden items-center gap-7 text-sm font-medium text-white/80 md:flex">
            <a href="#how" className="hover:text-white">How it works</a>
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#ai" className="hover:text-white">Technology</a>
          </nav>
          <div className="flex items-center gap-2">
            {user ? <Link to="/app" className="btn bg-white text-forest-900 hover:bg-cream-100">Open dashboard</Link> : <>
              <Link to="/login" className="btn text-white hover:bg-white/10">Log in</Link>
              <Link to="/register" className="btn bg-white text-forest-900 hover:bg-cream-100">Get started</Link>
            </>}
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="relative overflow-hidden bg-forest-900 pb-24 pt-36 text-white">
        <div className="absolute inset-0 opacity-[.18]" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, #97c09c 0, transparent 40%), radial-gradient(circle at 85% 60%, #649f6d 0, transparent 45%)" }} />
        <svg className="absolute -right-24 bottom-0 h-[520px] w-[520px] text-forest-800" viewBox="0 0 200 200" aria-hidden><path fill="currentColor" d="M40 180C40 90 90 30 190 20c-8 100-60 160-150 160Z" /><path d="M45 175 150 60" stroke="#1b3723" strokeWidth="3" /></svg>
        <div className="relative mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[1.15fr_.85fr] lg:items-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div className="chip mb-6 bg-white/10 text-forest-100 ring-1 ring-white/15"><Sprout className="h-3.5 w-3.5" /> AI-driven pest detection for Indian farms</div>
            <h1 className="text-4xl font-semibold leading-[1.05] sm:text-6xl">Spot the pest.<br /><span className="text-forest-300">Save the harvest.</span></h1>
            <p className="mt-6 max-w-xl text-lg text-forest-100/80">Photograph your crop or sticky trap. AgriGuard AI finds and counts pests, scores how serious the infestation is, and guides you to safe, integrated treatment — in Hindi, Hinglish or English.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to={user ? "/app/detect" : "/register"} className="btn bg-forest-300 px-6 py-3 text-base text-forest-950 hover:bg-forest-200">Scan your crop <ArrowRight className="h-4 w-4" /></Link>
              <a href="#how" className="btn px-6 py-3 text-base text-white ring-1 ring-white/25 hover:bg-white/10">See how it works</a>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-forest-100/70">
              <span className="flex items-center gap-1.5"><ShieldCheck className="h-4 w-4" /> IPM-first advice</span>
              <span className="flex items-center gap-1.5"><Languages className="h-4 w-4" /> हिंदी · Hinglish · English</span>
              <span className="flex items-center gap-1.5"><Camera className="h-4 w-4" /> Works from a phone camera</span>
            </div>
          </motion.div>
          <motion.div initial={{ opacity: 0, scale: .96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: .7, delay: .15 }} className="relative">
            <div className="rounded-3xl bg-white/[.06] p-4 ring-1 ring-white/10 backdrop-blur">
              <div className="rounded-2xl bg-cream-50 p-5 text-forest-950">
                <div className="flex items-center justify-between"><div className="text-xs font-semibold uppercase tracking-wide text-forest-900/50">Scan result</div><span className="chip bg-orange-100 text-orange-800">● High · 62</span></div>
                <div className="relative mt-4 h-44 overflow-hidden rounded-xl bg-gradient-to-br from-forest-300 via-forest-400 to-forest-600">
                  {[[18, 30, 22, 26], [52, 52, 18, 22], [70, 20, 16, 20]].map(([x, y, w, h], i) => (
                    <motion.div key={i} className="absolute rounded-md border-2 border-red-500" style={{ left: `${x}%`, top: `${y}%`, width: `${w}%`, height: `${h}%` }} initial={{ opacity: 0, scale: 1.3 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: .6 + i * .25 }}>
                      <span className="absolute -top-5 left-0 rounded bg-red-500 px-1 text-[10px] font-semibold text-white">pest</span>
                    </motion.div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] text-forest-900/50">Illustration of the result layout — not real data.</p>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  {[["Count", "per image"], ["Severity", "0–100 index"], ["Treatment", "IPM guidance"]].map(([a, b]) => <div key={a} className="rounded-lg bg-forest-50 p-2"><div className="font-semibold">{a}</div><div className="text-forest-900/50">{b}</div></div>)}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* verified stats */}
      <section className="border-b border-forest-900/10 bg-cream-100">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-6 px-5 py-10 md:grid-cols-4">
          {[
            [model?.num_classes ? String(model.num_classes) : "—", "pest classes the model recognises"],
            [totalImages ? totalImages.toLocaleString("en-IN") : "—", "annotated IP102 images used"],
            [typeof m.map50 === "number" ? `${(m.map50 * 100).toFixed(1)}%` : "—", "mAP@0.5 on the held-out test set"],
            [typeof m.f1 === "number" ? `${(m.f1 * 100).toFixed(1)}%` : "—", "F1-score on the test set"],
          ].map(([v, l]) => <motion.div key={l} {...fade}><div className="font-display text-4xl font-semibold text-forest-800">{v}</div><div className="mt-1 text-sm text-forest-900/60">{l}</div></motion.div>)}
        </div>
        <p className="mx-auto max-w-7xl px-5 pb-6 text-xs text-forest-900/50">
          {model?.available ? `Figures come live from the deployed model (${model.name} v${model.version}).` : "Figures appear here once the trained model is deployed — no placeholder numbers are shown."}
        </p>
      </section>

      {/* how */}
      <section id="how" className="mx-auto max-w-7xl px-5 py-24">
        <motion.div {...fade} className="max-w-2xl"><div className="text-xs font-semibold uppercase tracking-[.14em] text-forest-500">How it works</div><h2 className="mt-2 text-3xl font-semibold sm:text-4xl">From photo to action plan in seconds</h2></motion.div>
        <div className="mt-12 grid gap-6 md:grid-cols-4">
          {[[Camera, "1. Capture", "Upload or snap a photo of leaves, stems or a sticky trap."], [ScanSearch, "2. Detect", "A YOLO model trained on IP102 finds and counts each pest."], [Gauge, "3. Assess", "Density and a transparent severity score show how urgent it is."], [Leaf, "4. Act", "Get organic, biological and IPM-first treatment guidance."]].map(([Icon, t, d], i) => {
            const I = Icon as typeof Camera;
            return <motion.div key={t as string} {...fade} transition={{ delay: i * .08, duration: .5 }} className="card p-6"><div className="grid h-11 w-11 place-items-center rounded-xl bg-forest-100 text-forest-700"><I className="h-5 w-5" /></div><h3 className="mt-5 text-lg font-semibold">{t as string}</h3><p className="mt-1.5 text-sm text-forest-900/60">{d as string}</p></motion.div>;
          })}
        </div>
      </section>

      {/* features */}
      <section id="features" className="bg-white py-24">
        <div className="mx-auto max-w-7xl px-5">
          <motion.div {...fade} className="max-w-2xl"><div className="text-xs font-semibold uppercase tracking-[.14em] text-forest-500">Features</div><h2 className="mt-2 text-3xl font-semibold sm:text-4xl">Everything a farmer needs to stay ahead of pests</h2></motion.div>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[
              [ScanSearch, "Multi-pest detection", "Detect and count several pest species in one image, with bounding boxes and confidence."],
              [Gauge, "Severity meter", "A 0–100 index from density, pest species, crop stage and trend — every factor explained."],
              [BellRing, "Density alerts", "Set your own thresholds per pest. Get alerted when an infestation turns high or critical."],
              [Leaf, "IPM treatment guide", "Organic, biological and preventive options first. Chemical guidance only as registered classes."],
              [Bot, "AI Kisan chatbot", "Ask in Hindi, Hinglish or English. It knows your recent scans and crops."],
              [LineChart, "Analytics & reports", "Trends, pest distribution, crop statistics, CSV export and PDF reports."],
              [CloudSun, "Weather risk", "Live local weather with pest-risk hints and spray-timing advice."],
              [Camera, "Camera & batch scans", "Scan directly from your phone camera or upload up to 10 images at once."],
              [ShieldCheck, "Private by design", "Your farm data and images are visible only to you."],
            ].map(([Icon, t, d]) => { const I = Icon as typeof Camera; return (
              <motion.div key={t as string} {...fade} className="rounded-2xl border border-forest-900/10 p-6 transition hover:border-forest-300 hover:shadow-soft">
                <I className="h-6 w-6 text-forest-600" /><h3 className="mt-4 font-sans text-base font-semibold">{t as string}</h3><p className="mt-1 text-sm text-forest-900/60">{d as string}</p>
              </motion.div>); })}
          </div>
        </div>
      </section>

      {/* AI */}
      <section id="ai" className="mx-auto grid max-w-7xl gap-12 px-5 py-24 lg:grid-cols-2 lg:items-center">
        <motion.div {...fade}>
          <div className="text-xs font-semibold uppercase tracking-[.14em] text-forest-500">The technology</div>
          <h2 className="mt-2 text-3xl font-semibold sm:text-4xl">Real computer vision, honest numbers</h2>
          <p className="mt-4 text-forest-900/70">The detector is an Ultralytics YOLO model fine-tuned on the IP102 insect-pest benchmark (CVPR 2019) and served with ONNX Runtime. Metrics shown on this site come from evaluation on a held-out test split — nothing is invented.</p>
          <ul className="mt-6 space-y-3 text-sm">
            {["Transfer learning from COCO-pretrained YOLO weights", "Cleaned dataset: corrupt images, bad boxes and duplicates removed; leakage-free split", "Precision, recall, F1, mAP@0.5 and mAP@0.5:0.95 with a confusion matrix", "Low-confidence detections are flagged, never hidden"].map((t) => <li key={t} className="flex gap-2"><Cpu className="mt-0.5 h-4 w-4 shrink-0 text-forest-600" />{t}</li>)}
          </ul>
        </motion.div>
        <motion.div {...fade} className="card grain p-6">
          <div className="text-xs font-semibold uppercase tracking-wide text-forest-900/50">Model card</div>
          <dl className="mt-4 divide-y divide-forest-900/10 text-sm">
            {[["Architecture", model?.architecture ?? "YOLO (Ultralytics)"], ["Dataset", model?.dataset ?? "IP102 detection subset"], ["Classes", model?.num_classes ? String(model.num_classes) : "102"],
              ["Precision", typeof m.precision === "number" ? `${(m.precision * 100).toFixed(1)}%` : "pending evaluation"], ["Recall", typeof m.recall === "number" ? `${(m.recall * 100).toFixed(1)}%` : "pending evaluation"],
              ["mAP@0.5:0.95", typeof m.map50_95 === "number" ? `${(m.map50_95 * 100).toFixed(1)}%` : "pending evaluation"]].map(([k, v]) => (
              <div key={k} className="flex justify-between py-2.5"><dt className="text-forest-900/60">{k}</dt><dd className="font-semibold">{v}</dd></div>))}
          </dl>
        </motion.div>
      </section>

      {/* CTA */}
      <section className="px-5 pb-24">
        <div className="mx-auto max-w-5xl rounded-3xl bg-forest-800 px-8 py-14 text-center text-white">
          <h2 className="text-3xl font-semibold sm:text-4xl">Protect your next harvest</h2>
          <p className="mx-auto mt-3 max-w-xl text-forest-100/80">Create a free account, add your farm and crops, and run your first scan in under a minute.</p>
          <Link to={user ? "/app/detect" : "/register"} className="btn mt-8 bg-forest-300 px-6 py-3 text-base text-forest-950 hover:bg-forest-200">Start scanning <ArrowRight className="h-4 w-4" /></Link>
        </div>
      </section>

      <footer className="border-t border-forest-900/10 bg-cream-100">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-8 text-sm text-forest-900/60 md:flex-row md:items-center md:justify-between">
          <Logo />
          <p className="max-w-xl text-xs">AgriGuard AI gives decision support only. AI detections can be wrong — confirm in the field and consult your local KVK / agriculture officer before using any pesticide. Dataset: IP102 (Wu et al., CVPR 2019).</p>
          <p className="text-xs">© {new Date().getFullYear()} AgriGuard AI</p>
        </div>
      </footer>
    </div>
  );
}
