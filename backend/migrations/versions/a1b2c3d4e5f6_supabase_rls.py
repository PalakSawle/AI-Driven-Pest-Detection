"""Enable Row Level Security on all app tables (PostgreSQL / Supabase only).

The API connects as the database owner (bypasses RLS). With RLS on and no
policies, Supabase's public REST/GraphQL roles (anon, authenticated) cannot read
or write these tables directly, so users' detection records are only reachable
through the authenticated API, which filters every query by user.

Revision ID: a1b2c3d4e5f6
Revises: 872a37cc2c7e
"""
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "872a37cc2c7e"
branch_labels = None
depends_on = None

TABLES = ["users", "farms", "crops", "user_crops", "model_versions", "detections", "detected_instances",
          "severity_assessments", "density_observations", "alert_thresholds", "treatment_recommendations",
          "notifications", "chat_conversations", "chat_messages", "weather_records", "alembic_version"]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" DISABLE ROW LEVEL SECURITY')
