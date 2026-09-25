-- Research Studio DB Migration
-- Creates 3 new tables for the Research Paper job lifecycle:
--   research_paper_jobs   — top-level job tracking
--   research_evidence     — per-source evidence blocks
--   claim_evidence_mappings — Claim-Evidence Matrix rows
--
-- Run this migration once against the Neon PostgreSQL database.
-- Safe to run multiple times (uses CREATE TYPE IF NOT EXISTS, CREATE TABLE IF NOT EXISTS).

BEGIN;

-- ─── Enum: Research Job Status ───────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE researchjobstatus AS ENUM (
    'draft',
    'scrub_required',
    'awaiting_consent',
    'planning',
    'retrieving_sources',
    'extracting_evidence',
    'verifying_sources',
    'synthesizing',
    'citation_validation',
    'generating_artifacts',
    'needs_review',
    'approved',
    'rejected',
    'failed'
  );
EXCEPTION WHEN duplicate_object THEN
  -- Enum already exists; add any new values idempotently
  ALTER TYPE researchjobstatus ADD VALUE IF NOT EXISTS 'scrub_required';
  ALTER TYPE researchjobstatus ADD VALUE IF NOT EXISTS 'awaiting_consent';
  ALTER TYPE researchjobstatus ADD VALUE IF NOT EXISTS 'extracting_evidence';
  ALTER TYPE researchjobstatus ADD VALUE IF NOT EXISTS 'verifying_sources';
  ALTER TYPE researchjobstatus ADD VALUE IF NOT EXISTS 'citation_validation';
  ALTER TYPE researchjobstatus ADD VALUE IF NOT EXISTS 'generating_artifacts';
END $$;

-- ─── Table: research_paper_jobs ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.research_paper_jobs (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id               UUID        NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    status                  researchjobstatus NOT NULL DEFAULT 'draft',

    -- Paper metadata (user-supplied)
    paper_title             VARCHAR(512),
    authors                 JSONB,
    research_question       TEXT        NOT NULL,
    domain_keywords         JSONB,
    paper_type              VARCHAR(80) NOT NULL DEFAULT 'literature_review',
    depth                   VARCHAR(50) NOT NULL DEFAULT 'standard',
    citation_format         VARCHAR(30) NOT NULL DEFAULT 'ieee',
    date_from               VARCHAR(10),
    date_to                 VARCHAR(10),
    preferred_source_types  JSONB,
    excluded_domains        JSONB,

    -- PII scrub
    scrub_findings          JSONB,
    sanitized_question      TEXT,
    consent_confirmed       BOOLEAN     NOT NULL DEFAULT FALSE,
    consent_timestamp       TIMESTAMPTZ,

    -- Research plan
    research_plan           JSONB,
    executed_queries        JSONB,

    -- Provider summary
    providers_attempted     JSONB,
    providers_succeeded     JSONB,
    providers_failed        JSONB,
    sources_retrieved       INTEGER     NOT NULL DEFAULT 0,
    sources_excluded        INTEGER     NOT NULL DEFAULT 0,

    -- Evidence quality metrics
    evidence_coverage_pct   DOUBLE PRECISION,
    citation_validity_count INTEGER     NOT NULL DEFAULT 0,
    citation_total_count    INTEGER     NOT NULL DEFAULT 0,
    flagged_claims_count    INTEGER     NOT NULL DEFAULT 0,

    -- Generated content
    paper_content           TEXT,
    paper_outline           JSONB,
    artifact_pdf_path       VARCHAR(512),

    -- Validation + review
    citation_validation_result JSONB,
    review_checklist        JSONB,
    reviewer_notes          TEXT,
    approved_at             TIMESTAMPTZ,

    -- Failure tracking
    error_message           TEXT,
    failed_stage            VARCHAR(100),

    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_research_paper_jobs_report_id
    ON public.research_paper_jobs (report_id);
CREATE INDEX IF NOT EXISTS idx_research_paper_jobs_status
    ON public.research_paper_jobs (status);

-- ─── Table: research_evidence ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.research_evidence (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id               UUID        NOT NULL REFERENCES public.research_paper_jobs(id) ON DELETE CASCADE,

    -- Source provenance (from provider retrieval — never invented)
    provider             VARCHAR(60) NOT NULL,
    source_identifier    VARCHAR(256),
    canonical_url        VARCHAR(2048) NOT NULL,
    title                TEXT        NOT NULL,
    authors              JSONB,
    publisher            VARCHAR(512),
    publication_date     VARCHAR(20),
    source_class         VARCHAR(60) NOT NULL,
    access_level         VARCHAR(30) NOT NULL,

    -- Extracted text
    retrieved_excerpt    TEXT,
    location             VARCHAR(200),

    -- Quality
    topic_tags           JSONB,
    inclusion_reason     TEXT,
    exclusion_reason     TEXT,
    is_excluded          BOOLEAN     NOT NULL DEFAULT FALSE,

    retrieval_timestamp  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_evidence_job_id
    ON public.research_evidence (job_id);

-- ─── Table: claim_evidence_mappings ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.claim_evidence_mappings (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id                  UUID        NOT NULL REFERENCES public.research_paper_jobs(id) ON DELETE CASCADE,
    evidence_id             UUID        REFERENCES public.research_evidence(id) ON DELETE SET NULL,

    claim_id                VARCHAR(40) NOT NULL,
    claim_text              TEXT        NOT NULL,
    claim_type              VARCHAR(30) NOT NULL DEFAULT 'descriptive',
    citation_strength       VARCHAR(30) NOT NULL DEFAULT 'unsupported',
    requires_review         BOOLEAN     NOT NULL DEFAULT FALSE,
    section_reference       VARCHAR(100),
    inline_citation_marker  VARCHAR(20),

    -- Validation
    validation_passed       BOOLEAN,
    validation_note         TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claim_evidence_mappings_job_id
    ON public.claim_evidence_mappings (job_id);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_mappings_evidence_id
    ON public.claim_evidence_mappings (evidence_id);

COMMIT;
