-- ============================================================
-- BOTZI – Supabase Database Setup
-- ============================================================
-- Run this SQL in your Supabase project:
--   Dashboard → SQL Editor → New Query → Paste & Run
--
-- Creates 3 tables:
--   1. chat_interactions  – every Q&A log
--   2. feedback           – user star ratings
--   3. sync_log           – WorkDrive file sync state
-- ============================================================


-- ── 1. Chat Interactions ────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_interactions (
  id                BIGSERIAL PRIMARY KEY,
  session_id        TEXT        NOT NULL,
  user_id           TEXT        NOT NULL DEFAULT 'anonymous',
  question          TEXT        NOT NULL,
  answer            TEXT,
  sources           JSONB,                -- [{file_name, source, page, doc_type, score}]
  confidence        TEXT,                 -- high | medium | low
  response_time_ms  INTEGER,
  environment       TEXT DEFAULT 'prod',  -- dev | test | prod
  chunks_retrieved  INTEGER DEFAULT 0,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast analytics queries
CREATE INDEX IF NOT EXISTS idx_chat_user_id    ON chat_interactions (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_interactions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_session    ON chat_interactions (session_id);


-- ── 2. Feedback ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
  id          BIGSERIAL PRIMARY KEY,
  session_id  TEXT        NOT NULL,
  user_id     TEXT        NOT NULL DEFAULT 'anonymous',
  question    TEXT,
  rating      SMALLINT    NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment     TEXT,
  helpful     BOOLEAN,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_rating     ON feedback (rating);


-- ── 3. Sync Log (Zoho WorkDrive → Pinecone) ─────────────
CREATE TABLE IF NOT EXISTS sync_log (
  file_id    TEXT        PRIMARY KEY,   -- Zoho file ID (unique)
  file_name  TEXT        NOT NULL,
  modified   TEXT,                      -- Zoho last-modified timestamp
  chunks     INTEGER DEFAULT 0,         -- number of vectors upserted
  synced_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ── Useful Views ─────────────────────────────────────────

-- Daily usage summary
CREATE OR REPLACE VIEW daily_usage AS
SELECT
  DATE(created_at) AS day,
  COUNT(*)                              AS total_questions,
  COUNT(DISTINCT user_id)               AS unique_users,
  ROUND(AVG(response_time_ms))          AS avg_response_ms,
  ROUND(AVG(CASE confidence WHEN 'high' THEN 1.0 ELSE 0.0 END) * 100, 1) AS high_confidence_pct
FROM chat_interactions
GROUP BY DATE(created_at)
ORDER BY day DESC;


-- Average rating per day
CREATE OR REPLACE VIEW daily_ratings AS
SELECT
  DATE(created_at)       AS day,
  ROUND(AVG(rating), 2)  AS avg_rating,
  COUNT(*)               AS total_ratings
FROM feedback
GROUP BY DATE(created_at)
ORDER BY day DESC;


-- ============================================================
-- Enable Row Level Security (RLS) – optional but recommended
-- ============================================================
ALTER TABLE chat_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_log          ENABLE ROW LEVEL SECURITY;

-- Allow service_role (your API key) full access
CREATE POLICY "service_role_all" ON chat_interactions
  FOR ALL TO service_role USING (true);

CREATE POLICY "service_role_all" ON feedback
  FOR ALL TO service_role USING (true);

CREATE POLICY "service_role_all" ON sync_log
  FOR ALL TO service_role USING (true);

-- ============================================================
-- Done! You should now see these tables in your Supabase
-- Table Editor.
-- ============================================================
