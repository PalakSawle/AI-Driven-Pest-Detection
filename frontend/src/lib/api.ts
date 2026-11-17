// Typed API client for the AgriGuard FastAPI backend.
export const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
const TOKEN_KEY = "agriguard_token";

export const tokenStore = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set: (t: string) => { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ } },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const fileUrl = (path?: string | null) => (path ? `${API_URL}${path}` : "");

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers = new Headers(opts.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (opts.body && !(opts.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...opts, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the AgriGuard server. Check your connection and try again.");
  }
  if (res.status === 401 && token) {
    tokenStore.clear();
    window.dispatchEvent(new Event("agriguard:logout"));
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: { msg: string }) => d.msg).join("; ") : msg;
    } catch { /* not json */ }
    throw new ApiError(res.status, msg || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? res.json() : res.blob()) as Promise<T>;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) => request<T>(p, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  patch: <T>(p: string, body?: unknown) => request<T>(p, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  put: <T>(p: string, body?: unknown) => request<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
  download: async (p: string, filename: string) => {
    const blob = await request<Blob>(p);
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },
};

export const qs = (o: Record<string, string | number | boolean | undefined | null>) => {
  const s = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") s.set(k, String(v)); });
  const str = s.toString();
  return str ? `?${str}` : "";
};

// ---------- types ----------
export type Level = "safe" | "low" | "moderate" | "high" | "critical";
export interface User { id: number; email: string; full_name: string; phone: string | null; role: "farmer" | "admin"; language: "en" | "hi" | "hinglish"; email_alerts: boolean; created_at: string; }
export interface Crop { id: number; key: string; name: string; name_hi: string; growth_stages: string[]; }
export interface Farm { id: number; name: string; location_name: string | null; state: string | null; latitude: number | null; longitude: number | null; area_hectares: number | null; }
export interface Profile extends User { farms: Farm[]; crops: Crop[]; }
export interface Instance { id: number; pest_class: string; confidence: number; x1: number; y1: number; x2: number; y2: number; low_confidence: boolean; }
export interface Severity { score: number; level: Level; factors: { name: string; value: string | number; effect: string }[]; explanation: string; recommended_action: string; }
export interface Density { pest_class: string; count: number; value: number; unit: string; method: string; level: string; }
export interface DetectionSummary { id: number; created_at: string; total_count: number; status: string; crop_name: string | null; growth_stage: string | null; severity_level: Level | null; severity_score: number | null; top_pest: string | null; mean_confidence: number | null; image_url: string; annotated_url: string | null; }
export interface Detection extends DetectionSummary { image_width: number; image_height: number; inference_ms: number; low_confidence_count: number; sample_type: string; trap_area_cm2: number | null; observation_hours: number | null; notes: string | null; class_counts: Record<string, number>; instances: Instance[]; severity: Severity | null; densities: Density[]; model_version: string | null; warnings: string[]; }
export interface Paginated { items: DetectionSummary[]; total: number; page: number; page_size: number; }
export interface Treatment { pest_key: string; common_name: string; common_name_hi: string | null; scientific_name: string | null; crops: string[]; symptoms: string[]; organic: string[]; biological: string[]; chemical_categories: { class: string; note: string }[]; preventive: string[]; ipm: string[]; monitoring: string; etl_note: string | null; references: { title: string; url: string }[]; curated: boolean; safety: string[]; expert_advice_required: boolean; }
export interface Notification { id: number; type: string; title: string; message: string; level: string; detection_id: number | null; is_read: boolean; due_at: string | null; created_at: string; }
export interface ChatMessage { id: number; role: "user" | "assistant"; content: string; language: string | null; source: string | null; created_at: string; }
export interface Threshold { id: number; user_id: number | null; pest_class: string; low: number; moderate: number; high: number; critical: number; }
export interface Overview { total_scans: number; total_pests: number; scans_with_pests: number; most_frequent_pest: string | null; high_risk_detections: number; average_confidence: number | null; pest_distribution: { pest: string; count: number }[]; severity_distribution: { level: Level; count: number }[]; crop_stats: { crop: string; scans: number; pests: number; high_risk: number }[]; recent: { id: number; created_at: string; total_count: number; top_pest: string | null; severity_level: Level | null; severity_score: number | null }[]; has_unread_alerts: boolean; }
export interface Trends { period: string; series: { period: string; scans: number; pests: number; high_risk: number; avg_severity: number; avg_confidence: number | null }[]; density: { date: string; pest: string; value: number; unit: string; level: string; detection_id: number }[]; }
export interface ModelInfo { available: boolean; name: string | null; version: string | null; architecture: string | null; dataset: string | null; dataset_source: string | null; num_classes: number; classes: string[]; metrics: Record<string, number | Record<string, number> | string>; per_class: Record<string, { precision: number; recall: number; f1: number; map50: number; map50_95: number }>; dataset_stats: Record<string, unknown>; thresholds: { confidence: number; low_confidence: number }; }
