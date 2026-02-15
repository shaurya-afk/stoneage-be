-- Extraction tables for PDF data pipeline
-- Run this in Supabase SQL Editor (Dashboard -> SQL Editor)
-- or via any PostgreSQL client.
--
-- Required .env for SQLAlchemy ORM:
--   DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
-- Get from Supabase: Settings -> Database -> Connection string (URI)

-- Raw extraction inputs (before processing)
CREATE TABLE IF NOT EXISTS extraction_raw (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    fields JSONB NOT NULL,
    llm_model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Processed extraction results
CREATE TABLE IF NOT EXISTS extraction_processed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_id UUID REFERENCES extraction_raw(id) ON DELETE SET NULL,
    file_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    fields JSONB NOT NULL,
    response JSONB NOT NULL,
    llm_model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional: indexes for common queries
CREATE INDEX IF NOT EXISTS idx_extraction_raw_created_at ON extraction_raw(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_extraction_raw_document_type ON extraction_raw(document_type);
CREATE INDEX IF NOT EXISTS idx_extraction_processed_created_at ON extraction_processed(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_extraction_processed_raw_id ON extraction_processed(raw_id);
