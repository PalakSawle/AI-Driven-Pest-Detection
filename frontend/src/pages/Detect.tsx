import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, FileImage, ImagePlus, Info, Loader2, RefreshCw, ScanSearch, Trash2, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Card, ConfidenceBar, DetectionImage, ErrorBox, LevelBadge, PageHeader, SeverityMeter, Toggle } from "../components/ui";
import { api, type Crop, type Detection, type ModelInfo, type Profile } from "../lib/api";
import { titleCase, useApi } from "../lib/hooks";

const MAX_MB = 8;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function Detect() {
  const crops = useApi<Crop[]>("/api/crops");
  const profile = useApi<Profile>("/api/profile");
  const model = useApi<ModelInfo>("/api/model/info");
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [cropId, setCropId] = useState<string>("");
  const [stage, setStage] = useState("");
  const [sampleType, setSampleType] = useState("field_photo");
  const [trapArea, setTrapArea] = useState(""); const [hours, setHours] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [results, setResults] = useState<Detection[]>([]);
  const [camera, setCamera] = useState(false);
  const [drag, setDrag] = useState(false);
  const [showBoxes, setShowBoxes] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!cropId && profile.data?.crops.length) setCropId(String(profile.data.crops[0].id));
  }, [profile.data, cropId]);
  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [files]);

  const crop = crops.data?.find((c) => String(c.id) === cropId);
  const addFiles = (list: FileList | File[]) => {
    setErr(null);
    const arr = Array.from(list);
    const bad = arr.find((f) => !TYPES.includes(f.type));
    if (bad) return setErr(`"${bad.name}" is not a JPEG, PNG or WebP image.`);
    const big = arr.find((f) => f.size > MAX_MB * 1024 * 1024);
    if (big) return setErr(`"${big.name}" is larger than ${MAX_MB} MB.`);
    setFiles((cur) => [...cur, ...arr].slice(0, 10));
    setResults([]);
  };

  const run = async () => {
    if (!files.length) return;
    setBusy(true); setErr(null); setResults([]);
    const fd = new FormData();
    if (cropId) fd.append("crop_id", cropId);
    if (stage) fd.append("growth_stage", stage);
    fd.append("sample_type", sampleType);
    try {
      if (files.length === 1) {
        fd.append("image", files[0]);
        if (sampleType === "sticky_trap") { if (trapArea) fd.append("trap_area_cm2", trapArea); if (hours) fd.append("observation_hours", hours); }
        if (notes) fd.append("notes", notes);
        if (profile.data?.farms[0]) fd.append("farm_id", String(profile.data.farms[0].id));
        setResults([await api.post<Detection>("/api/detections/analyze", fd)]);
      } else {
        files.forEach((f) => fd.append("images", f));
        setResults(await api.post<Detection[]>("/api/detections/batch", fd));
      }
      window.dispatchEvent(new Event("agriguard:alerts"));
    } catch (e) { setErr((e as Error).message); }
    setBusy(false);
  };

  return (
    <div>
      <PageHeader eyebrow="AI pest detection" title="Scan your crop" subtitle="Upload a clear, close photo of affected leaves, stems or a sticky trap. Up to 10 images at once." />
      {model.data && !model.data.available && <div className="mb-4"><ErrorBox message="The pest-detection model is not loaded on the server yet. Scans will be possible as soon as the trained model is deployed." /></div>}
      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <Card>
          {camera ? <CameraCapture onCapture={(f) => { addFiles([f]); setCamera(false); }} onClose={() => setCamera(false)} /> : (
            <div
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files); }}
              className={clsx("flex min-h-[260px] flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition",
                drag ? "border-forest-500 bg-forest-50 dark:bg-forest-500/10" : "border-forest-900/15 dark:border-white/10")}>
              {previews.length ? (
                <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3">
                  {previews.map((p, i) => (
                    <div key={p} className="group relative aspect-square overflow-hidden rounded-xl bg-forest-950">
                      <img src={p} alt={files[i]?.name} className="h-full w-full object-cover" />
                      <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="absolute right-1.5 top-1.5 rounded-full bg-black/60 p-1 text-white opacity-0 transition group-hover:opacity-100" aria-label="Remove image"><X className="h-3.5 w-3.5" /></button>
                    </div>
                  ))}
                  {files.length < 10 && <button onClick={() => inputRef.current?.click()} className="grid aspect-square place-items-center rounded-xl border-2 border-dashed border-forest-900/15 text-forest-700 hover:bg-forest-50 dark:border-white/10 dark:text-forest-200 dark:hover:bg-white/5"><ImagePlus className="h-6 w-6" /></button>}
                </div>
              ) : (
                <>
                  <div className="grid h-14 w-14 place-items-center rounded-2xl bg-forest-100 text-forest-700 dark:bg-forest-500/15 dark:text-forest-300"><Upload className="h-6 w-6" /></div>
                  <p className="mt-4 font-semibold">Drag & drop images here</p>
                  <p className="muted mt-1 text-sm">JPEG, PNG or WebP · max {MAX_MB} MB each</p>
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    <button className="btn-primary" onClick={() => inputRef.current?.click()}><FileImage className="h-4 w-4" />Choose images</button>
                    <button className="btn-outline" onClick={() => setCamera(true)}><Camera className="h-4 w-4" />Use camera</button>
                  </div>
                </>
              )}
              <input ref={inputRef} type="file" accept={TYPES.join(",")} multiple hidden onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ""; }} />
            </div>
          )}
          {files.length > 0 && !camera && (
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="muted">{files.length} image{files.length > 1 && "s"} selected{files.length > 1 && " · batch mode"}</span>
              <div className="flex gap-2"><button className="btn-ghost !py-1.5" onClick={() => setCamera(true)}><Camera className="h-4 w-4" />Camera</button><button className="btn-ghost !py-1.5" onClick={() => { setFiles([]); setResults([]); }}><Trash2 className="h-4 w-4" />Clear</button></div>
            </div>
          )}
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold">Scan details</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label" htmlFor="crop">Crop</label>
                <select id="crop" className="input" value={cropId} onChange={(e) => { setCropId(e.target.value); setStage(""); }}>
                  <option value="">Not specified</option>{crops.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select></div>
              <div><label className="label" htmlFor="stage">Growth stage</label>
                <select id="stage" className="input" value={stage} onChange={(e) => setStage(e.target.value)} disabled={!crop}>
                  <option value="">Not specified</option>{crop?.growth_stages.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
                </select></div>
            </div>
            <div><label className="label">Sample type</label>
              <div className="grid grid-cols-3 gap-2">
                {[["field_photo", "Field photo"], ["leaf_sample", "Leaf sample"], ["sticky_trap", "Sticky trap"]].map(([v, l]) => (
                  <button key={v} type="button" onClick={() => setSampleType(v)} className={clsx("rounded-xl border px-2 py-2 text-xs font-semibold transition", sampleType === v ? "border-forest-600 bg-forest-50 text-forest-800 dark:bg-forest-500/15 dark:text-forest-100" : "border-forest-900/15 dark:border-white/10")}>{l}</button>
                ))}
              </div></div>
            <AnimatePresence>
              {sampleType === "sticky_trap" && files.length <= 1 && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="label" htmlFor="area">Trap area (cm²)</label><input id="area" type="number" min="1" className="input" value={trapArea} onChange={(e) => setTrapArea(e.target.value)} placeholder="e.g. 250" /></div>
                    <div><label className="label" htmlFor="hours">Hours in field</label><input id="hours" type="number" min="1" className="input" value={hours} onChange={(e) => setHours(e.target.value)} placeholder="e.g. 48" /></div>
                  </div>
                  <p className="muted mt-2 flex gap-1.5 text-xs"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />With both values we report a trap-catch rate (pests / 100 cm² / day). Without them, only an image-based count.</p>
                </motion.div>
              )}
            </AnimatePresence>
            {files.length <= 1 && <div><label className="label" htmlFor="notes">Notes (optional)</label><input id="notes" className="input" maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. north corner of field" /></div>}
            {err && <ErrorBox message={err} />}
            <button className="btn-primary w-full !py-3" disabled={!files.length || busy} onClick={run}>
              {busy ? <><Loader2 className="h-4 w-4 animate-spin" />Analysing {files.length > 1 ? `${files.length} images` : "image"}…</> : <><ScanSearch className="h-4 w-4" />Detect pests</>}
            </button>
          </div>
        </Card>
      </div>

      <AnimatePresence>
        {results.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mt-8 space-y-6">
            <div className="flex items-center justify-between"><h2 className="text-2xl font-semibold">Results</h2><Toggle checked={showBoxes} onChange={setShowBoxes} label="Show boxes" /></div>
            {results.map((d) => <ResultCard key={d.id} d={d} showBoxes={showBoxes} />)}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ResultCard({ d, showBoxes }: { d: Detection; showBoxes: boolean }) {
  return (
    <Card className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
      <div>
        <DetectionImage src={d.image_url} width={d.image_width} height={d.image_height} instances={d.instances} showBoxes={showBoxes} />
        <div className="muted mt-2 flex flex-wrap gap-x-4 text-xs"><span>Inference {d.inference_ms.toFixed(0)} ms</span><span>Model {d.model_version ?? "—"}</span><span>{d.image_width}×{d.image_height}px</span><span>Dashed box = low confidence</span></div>
      </div>
      <div className="space-y-5">
        {d.warnings.map((w) => <div key={w} className="flex gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200"><Info className="mt-0.5 h-4 w-4 shrink-0" />{w}</div>)}
        <div className="flex items-center justify-between">
          <div><div className="muted text-xs font-semibold uppercase tracking-wide">Total pests</div><div className="font-display text-4xl font-semibold">{d.total_count}</div></div>
          {d.severity && <SeverityMeter score={d.severity.score} level={d.severity.level} size={170} />}
        </div>
        {Object.keys(d.class_counts).length > 0 && (
          <div>
            <div className="label">Detected species</div>
            <div className="space-y-2.5">
              {Object.entries(d.class_counts).map(([p, n]) => {
                const confs = d.instances.filter((i) => i.pest_class === p).map((i) => i.confidence);
                const dens = d.densities.find((x) => x.pest_class === p);
                return (
                  <div key={p} className="rounded-xl border border-forest-900/[.07] p-3 dark:border-white/10">
                    <div className="flex items-center justify-between gap-2"><Link to={`/app/treatments/${encodeURIComponent(p)}`} className="font-semibold hover:underline">{titleCase(p)}</Link><span className="chip bg-forest-100 text-forest-800 dark:bg-white/10 dark:text-forest-100">×{n}</span></div>
                    <div className="mt-2"><ConfidenceBar value={Math.max(...confs)} /></div>
                    {dens && <div className="muted mt-1.5 flex items-center justify-between text-xs"><span>{dens.value} {dens.unit}</span><LevelBadge level={dens.level} /></div>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {d.severity && <p className="text-sm"><span className="font-semibold">Next step: </span>{d.severity.recommended_action}</p>}
        <div className="flex flex-wrap gap-2">
          <Link to={`/app/detections/${d.id}`} className="btn-primary">Full analysis & treatment</Link>
          <button className="btn-outline" onClick={() => api.download(`/api/detections/${d.id}/report.pdf`, `agriguard_report_${d.id}.pdf`)}>PDF report</button>
        </div>
      </div>
    </Card>
  );
}

function CameraCapture({ onCapture, onClose }: { onCapture: (f: File) => void; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  useEffect(() => {
    let s: MediaStream | null = null;
    (async () => {
      try {
        s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing, width: { ideal: 1920 } }, audio: false });
        setStream(s); if (video.current) video.current.srcObject = s;
      } catch { setErr("Camera not available. Allow camera access, or use 'Choose images' (on phones this can open the camera too)."); }
    })();
    return () => s?.getTracks().forEach((t) => t.stop());
  }, [facing]);
  const snap = () => {
    const v = video.current; if (!v) return;
    const c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d")!.drawImage(v, 0, 0);
    c.toBlob((b) => b && onCapture(new File([b], `camera_${Date.now()}.jpg`, { type: "image/jpeg" })), "image/jpeg", 0.92);
  };
  return (
    <div>
      {err ? <ErrorBox message={err} /> : <video ref={video} autoPlay playsInline muted className="aspect-video w-full rounded-2xl bg-black object-cover" />}
      <div className="mt-3 flex justify-center gap-2">
        <button className="btn-outline" onClick={onClose}><X className="h-4 w-4" />Cancel</button>
        {!err && <button className="btn-outline" onClick={() => setFacing(facing === "environment" ? "user" : "environment")}><RefreshCw className="h-4 w-4" />Flip</button>}
        {!err && <button className="btn-primary" onClick={snap} disabled={!stream}><Camera className="h-4 w-4" />Capture</button>}
      </div>
    </div>
  );
}
