-- Supabase hardening: the FastAPI backend is the only client of these tables and connects
-- with the database owner role (which bypasses RLS). Enabling RLS with NO policies blocks
-- direct access through Supabase's public REST/GraphQL APIs (anon / authenticated roles),
-- so one user's detection records can never be read by another user outside the API.
-- Per-user isolation inside the API is enforced on every query (user_id filters; tested).
ALTER TABLE public.crops ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.treatment_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_thresholds ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_crops ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weather_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.density_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.detected_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.severity_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;

-- Private storage bucket for uploaded and annotated images (served via signed API URLs).
INSERT INTO storage.buckets (id, name, public) VALUES ('detections', 'detections', false)
ON CONFLICT (id) DO UPDATE SET public = false;
