CREATE TABLE IF NOT EXISTS jobs (
  id            BIGSERIAL PRIMARY KEY,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_type   TEXT NOT NULL DEFAULT 'auto',
  source_url    TEXT NOT NULL,
  title         TEXT,
  status        TEXT NOT NULL DEFAULT 'queued',
  stage         TEXT,
  progress      INT  NOT NULL DEFAULT 0,
  message       TEXT,
  log           TEXT,
  output_path   TEXT,
  output_key    TEXT,
  output_url    TEXT,
  output_size   BIGINT,
  tg_file_id    TEXT,
  sub_sinhala   TEXT,
  sub_english   TEXT,
  error         TEXT,
  attempts      INT  NOT NULL DEFAULT 0,
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);

INSERT INTO settings(key,value) VALUES
  ('encode_crf','22'),
  ('encode_preset','medium'),
  ('audio_mode','aac_stereo'),
  ('tg_caption_template','{title} | x264 | Sinhala+English soft subs')
ON CONFLICT DO NOTHING;