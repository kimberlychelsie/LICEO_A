-- ============================================================
-- SHS Pathways Management Table
-- Single source of truth for all SHS tracks and pathways
-- SAFE: All statements are idempotent (IF NOT EXISTS)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.shs_pathways (
    pathway_id    SERIAL PRIMARY KEY,
    branch_id     INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    track_name    VARCHAR(100) NOT NULL,   -- e.g. "Academic", "TVL", "Sports", "Arts and Design"
    pathway_name  VARCHAR(200) NOT NULL,   -- e.g. "STEM", "ABM", "HUMSS", "GAS", "ICT"
    description   TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_branch_track_pathway UNIQUE (branch_id, track_name, pathway_name)
);

CREATE INDEX IF NOT EXISTS idx_shs_pathways_branch ON public.shs_pathways (branch_id);
CREATE INDEX IF NOT EXISTS idx_shs_pathways_active ON public.shs_pathways (branch_id, is_active);

DO $$
BEGIN
    RAISE NOTICE 'SHS Pathways table created successfully.';
END $$;
