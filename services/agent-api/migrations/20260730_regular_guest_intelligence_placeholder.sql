-- Regular Guest Intelligence (FND-04) schema.
--
-- Normalized tables, indexes, checks and foreign keys for
-- docs/REGULAR_GUEST_INTELLIGENCE_MVP_SPEC.md #12 "Data model proposal".
--
-- This file is a checked-in DDL record for manual/ops application. The
-- application's own startup path applies the equivalent schema via
-- SQLAlchemy's Base.metadata.create_all() in
-- app/db/ingest_data.py:run_schema_migrations(), which is the mechanism
-- exercised by tests/test_migration.py. Every statement below is
-- idempotent (IF NOT EXISTS / DO $$ ... $$ guards) so it is safe to
-- reapply and never deletes or overwrites existing rows.

BEGIN;

CREATE TABLE IF NOT EXISTS bars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bar_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bar_id UUID NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_bar_memberships_bar_user UNIQUE (bar_id, user_id),
    CONSTRAINT ck_bar_memberships_role CHECK (role IN ('owner', 'manager', 'bartender'))
);

CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL only for persisted global records; every house/bespoke recipe is bar-owned.
    bar_id UUID NULL REFERENCES bars(id) ON DELETE CASCADE,
    source VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    current_version_id UUID NULL,
    derived_from_recipe_id UUID NULL REFERENCES recipes(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_recipes_source CHECK (source IN ('global', 'house', 'bespoke')),
    CONSTRAINT ck_recipes_status CHECK (status IN ('draft', 'active', 'archived'))
);

CREATE INDEX IF NOT EXISTS ix_recipes_bar_id ON recipes (bar_id);

CREATE TABLE IF NOT EXISTS recipe_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    ingredients JSONB NOT NULL,
    technique TEXT NULL,
    glassware VARCHAR(255) NULL,
    garnish TEXT NULL,
    flavor_profile JSONB NULL,
    total_volume_ml DOUBLE PRECISION NULL,
    estimated_abv DOUBLE PRECISION NULL,
    estimated_cost_vnd DOUBLE PRECISION NULL,
    calculation_metadata JSONB NULL,
    created_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_recipe_versions_recipe_version UNIQUE (recipe_id, version_number)
);

CREATE TABLE IF NOT EXISTS menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bar_id UUID NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_menus_status CHECK (status IN ('draft', 'active', 'archived'))
);

CREATE TABLE IF NOT EXISTS menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    menu_id UUID NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    display_name VARCHAR(255) NULL,
    section VARCHAR(100) NULL,
    selling_price_vnd DOUBLE PRECISION NULL,
    is_available BOOLEAN NOT NULL DEFAULT true,
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- MVP: a recipe appears at most once per menu.
    CONSTRAINT uq_menu_items_menu_recipe UNIQUE (menu_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS patrons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bar_id UUID NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
    display_name VARCHAR(255) NOT NULL,
    pronouns VARCHAR(100) NULL,
    service_notes TEXT NULL,
    allergies JSONB NULL,
    avoidances JSONB NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Pilot requires affirmative notice opt-in (FND-01 decision D4); the
    -- acknowledging principal is recorded, never inferred.
    notice_acknowledged_at TIMESTAMPTZ NULL,
    notice_version VARCHAR(32) NULL,
    notice_acknowledged_by_principal VARCHAR(255) NULL,
    CONSTRAINT ck_patrons_status CHECK (status IN ('active', 'archived'))
);

CREATE INDEX IF NOT EXISTS ix_patrons_bar_id_display_name ON patrons (bar_id, display_name);

CREATE TABLE IF NOT EXISTS drink_experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bar_id UUID NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
    patron_id UUID NOT NULL REFERENCES patrons(id) ON DELETE CASCADE,
    recipe_id UUID NULL REFERENCES recipes(id) ON DELETE SET NULL,
    recipe_version_id UUID NULL REFERENCES recipe_versions(id) ON DELETE SET NULL,
    -- Server-built snapshot (PTR-03); the source of truth even if the
    -- recipe is edited or deleted later.
    recipe_snapshot JSONB NOT NULL,
    rating SMALLINT NULL,
    feedback TEXT NULL,
    feedback_provenance VARCHAR(32) NULL,
    served_at TIMESTAMPTZ NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    created_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_drink_experiences_rating_range CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5)),
    CONSTRAINT ck_drink_experiences_feedback_provenance_values CHECK (
        feedback_provenance IS NULL OR feedback_provenance IN ('guest_stated', 'bartender_observed')
    ),
    -- FND-01 decision D2: rating/feedback requires stated provenance.
    CONSTRAINT ck_drink_experiences_provenance_required CHECK (
        (rating IS NULL AND feedback IS NULL) OR feedback_provenance IS NOT NULL
    ),
    CONSTRAINT uq_drink_experiences_bar_idempotency_key UNIQUE (bar_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS taste_profiles (
    patron_id UUID PRIMARY KEY REFERENCES patrons(id) ON DELETE CASCADE,
    bar_id UUID NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
    profile JSONB NULL,
    evidence_summary JSONB NULL,
    eligible_experience_count INTEGER NOT NULL DEFAULT 0,
    confidence_score DOUBLE PRECISION NULL,
    confidence_label VARCHAR(32) NULL,
    profile_version VARCHAR(32) NULL,
    computed_at TIMESTAMPTZ NULL,
    is_stale BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT ck_taste_profiles_confidence_label CHECK (
        confidence_label IS NULL OR confidence_label IN ('no_data', 'low', 'emerging', 'moderate', 'high')
    )
);

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bar_id UUID NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
    patron_id UUID NOT NULL REFERENCES patrons(id) ON DELETE CASCADE,
    candidate_recipe_snapshot JSONB NOT NULL,
    match_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    score_breakdown JSONB NOT NULL,
    scoring_version VARCHAR(32) NOT NULL,
    rationale TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'generated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_recommendations_status CHECK (status IN ('generated', 'saved', 'served', 'dismissed'))
);

CREATE INDEX IF NOT EXISTS ix_recommendations_bar_patron ON recommendations (bar_id, patron_id);

-- Stable natural key on the pre-existing liquor_prices table so ingestion
-- can upsert instead of the prior unconditional delete-and-reinsert. Added
-- with a guard because the table predates this migration.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_liquor_prices_name_size_raw'
    ) THEN
        ALTER TABLE liquor_prices
            ADD CONSTRAINT uq_liquor_prices_name_size_raw UNIQUE (name, size_raw);
    END IF;
END $$;

COMMIT;
