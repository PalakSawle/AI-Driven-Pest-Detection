# AgriGuard AI — Smart Pest Detection & Intelligent Crop Protection

AI-powered web platform that detects and counts agricultural insect pests from photos, scores infestation
severity with a transparent method, recommends IPM-first treatments, and answers farmers' questions in
Hindi, Hinglish and English.

> Decision support only. AI detections can be wrong — confirm in the field and consult your local KVK /
> agriculture officer before applying any pesticide.

## Architecture

```
┌──────────────┐  HTTPS/JSON   ┌───────────────────────────┐   SQL    ┌──────────────────────┐
│ React (Vite) │ ────────────▶ │ FastAPI  (backend/app)    │ ───────▶ │ PostgreSQL (Supabase) │
│ Vercel       │ ◀──────────── │ Render (Docker)           │          └──────────────────────┘
└──────────────┘  signed URLs  │  ├─ ONNX Runtime YOLO     │  REST    ┌──────────────────────┐
                               │  ├─ density / severity    │ ───────▶ │ Supabase Storage      │
                               │  ├─ IPM knowledge base    │          │ (private bucket)      │
                               │  ├─ AI Kisan chat ──▶ LLM API (optional) / KB fallback        │
                               │  └─ weather ──▶ Open-Meteo                                     │
                               └───────────────────────────┘
ml/  dataset prep + YOLO training/eval (Kaggle/Colab GPU) ──▶ best.onnx + model_meta.json
```

| Folder | Contents |
|---|---|
| `backend/app/` | FastAPI app: `routers/` (API), `services/` (detector, scoring, alerts, chat, weather, reports, storage), `models.py` (schema), `data/treatments_kb.py` |
| `backend/migrations/` | Alembic migrations + `001_initial_postgres.sql`, `002_supabase_rls_and_storage.sql` |
| `backend/tests/` | 18 API/unit tests (pytest) |
| `backend/weights/` | `best.onnx` + `model_meta.json` (trained model, served by ONNX Runtime) |
| `frontend/` | React 18 + TypeScript + Tailwind + Framer Motion + Recharts + Lucide |
| `ml/` | `dataset/prepare_ip102.py`, `training/train.py`, `training/evaluate.py`, `run_kaggle.sh`, Colab notebook |
| `e2e/run_e2e.py` | Playwright browser test of the whole user journey |

## Dataset

**IP102 detection subset** — Wu et al., *IP102: A Large-Scale Benchmark Dataset for Insect Pest Recognition*, CVPR 2019.
- Homepage: https://github.com/xpwu95/IP102 (official Google Drive mirror linked there)
- Kaggle mirror used for training: https://www.kaggle.com/datasets/parserpixy/ip102-dataset (Pascal VOC XML + official `trainval.txt` / `test.txt`; listed on Kaggle under ODC-PDDL)
- Licence note: the original authors publish no explicit licence and ask for citation — use for research/education and cite the paper.
- 102 classes in 8 crop super-classes (rice, corn, wheat, beet, alfalfa, grape, citrus, mango).

`ml/dataset/prepare_ip102.py` (re-runnable): parses VOC XML → maps numeric labels to `classes.txt` names →
removes corrupt images, degenerate/out-of-bounds boxes, invalid labels and exact duplicate images (SHA-1) →
uses the **official test split** (val = 10 % of trainval, seed 42) so no image leaks between splits → writes YOLO labels,
`data.yaml` and `dataset_stats.json` (images per split, boxes per class, cleaning counts).

<!-- DATASET_STATS -->

## Model & evaluation

Ultralytics **YOLO11s**, transfer learning from COCO weights, 640 px, cosine LR, early stopping; exported to ONNX
(opset 12) and served with ONNX Runtime (letterbox + class-aware NMS re-implemented in `services/detector.py`).

<!-- METRICS -->

Metrics come from `ml/training/evaluate.py` on the held-out **test** split; they are stored in `backend/weights/model_meta.json`
and shown live in the app (landing page, Analytics, Admin).

## Density & severity methodology (transparent, configurable — not a validated yield model)

**Density** per pest per scan:
- Field photo / leaf sample → `pests/image` — an *estimated image-based count* (relative index). No pests-per-m² claim.
- Sticky trap **with** trap area and hours in field → `count / (area/100 cm²) / (hours/24)` = pests/100 cm²/day.
- Compared with per-pest thresholds (user-configurable; system defaults are starting points) → none/low/moderate/high/critical.

**Severity score (0–100)** = `(D × W × S + T + V) × C`
D = 60 × min(density / critical threshold, 1) · W = pest damage weight from the knowledge base (0.7–1.4) ·
S = crop growth-stage sensitivity (0.7–1.4) · T = trend (+15 if rising over the last 3 scans in 14 days, +8 if already high) ·
V = +5 per extra species (max 10) · C = 0.85 if mean confidence < 0.5.
Levels: 0 detections = Safe, < 25 Low, < 50 Moderate, < 75 High, ≥ 75 Critical. Every factor is shown to the user.

## Treatment engine

`backend/app/data/treatments_kb.py` — curated IPM entries for ~28 economically important pests (symptoms, organic,
biological, preventive, IPM, monitoring, ETL notes, references to NCIPM/ICAR, DPPQS/NIPHM, TNAU, FAO, IRAC). Chemical
guidance is limited to **insecticide classes (IRAC groups)** — no brand names, doses or schedules — with CIB&RC
registration and label/PPE warnings. The remaining IP102 classes get clearly-marked general IPM guidance with
"expert advice required". Have an agronomist review the content before production use.

## AI Kisan chatbot

`LLM_PROVIDER=anthropic|openai|gemini` + `LLM_API_KEY` → LLM answers grounded on the user's recent scans and the
knowledge base, with a safety system prompt (no doses/brands, KVK referral). Without a key (or on provider error) it
answers from the curated knowledge base (intent + entity matching in English / Hinglish / Hindi) and labels the source.

## API (OpenAPI docs at `/docs`)

`POST /api/auth/register · /login · /forgot-password · /reset-password · /change-password` · `GET /api/auth/me`
`POST /api/detections/analyze · /batch` · `GET /api/detections/history · /export.csv · /{id} · /{id}/report.pdf` · `DELETE /api/detections/{id}`
`GET /api/analytics/overview · /trends · /filters` · `GET /api/alerts · /unread-count` · `PATCH /api/alerts/{id}/read` · `POST /api/alerts/read-all` · `GET|PUT /api/alerts/thresholds`
`GET /api/treatments · /api/treatments/{pest}` · `POST /api/chat/message` · `GET /api/chat/history · /conversations · /status`
`GET /api/weather` · `GET /api/crops` · `GET|PATCH /api/profile` · `POST /api/farms` · `GET /api/model/info` · `GET /api/admin/stats · /users · /alerts`

Security: bcrypt passwords, JWT bearer auth, per-user filtering on every query (tested), admin RBAC, rate limits
(slowapi), upload type/size/decoding validation, private storage with expiring HMAC-signed image URLs, RLS enabled on
all Supabase tables (blocks public REST access), no secrets in the frontend.

## Run locally

```bash
# backend
cd backend
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                               # SQLite + Open-Meteo work with no keys
uvicorn app.main:app --reload                      # http://localhost:8000/docs
pytest -q                                          # 18 tests

# frontend (new terminal)
cd frontend
npm install
npm run dev                                        # http://localhost:5173 (proxies /api to :8000)
```
To create an admin set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env` before starting.

## Train / retrain the model

Kaggle (recommended, free GPU): new notebook → Settings → Accelerator **GPU T4 x2**, Internet **on** →
copy the `ml/` folder in (or `%%writefile` it) → `!bash ml/run_kaggle.sh` → *Save & Run All*.
Colab: open `ml/AgriGuard_Train_IP102.ipynb`, Runtime → T4 GPU → Run all.
Then copy `best.onnx` and `model_meta.json` from `agriguard_model.zip` into `backend/weights/`.

## Deploy

1. **Supabase**: new project (region Mumbai). No manual SQL needed — on every start the API runs `alembic upgrade head`
   (creates all tables + indexes and enables RLS on every table) and creates the private `detections` storage bucket.
   (`backend/migrations/001_initial_postgres.sql` / `002_…sql` are the same schema as plain SQL, if you prefer the SQL editor.)
   Copy **Connect → Session pooler** URI (IPv4 — Render cannot reach the IPv6-only direct host) and the `service_role` key.
2. **Render**: New → Web Service → this repo, root `backend`, Docker. Env vars from `backend/.env.example`
   (`DATABASE_URL`, `JWT_SECRET`, `STORAGE_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CORS_ORIGINS=https://<your-app>.vercel.app`, `FRONTEND_URL`, optional `LLM_*`, `SMTP_*`, `ADMIN_*`).
3. **Vercel**: import repo, root `frontend`, env `VITE_API_URL=https://<your-api>.onrender.com`.

<!-- DEPLOYMENT -->
