-- Add file_content (PDF bytes) to extraction_raw
ALTER TABLE extraction_raw ADD COLUMN IF NOT EXISTS file_content BYTEA;
