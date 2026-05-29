CREATE TABLE IF NOT EXISTS api_calls (
    id        BIGSERIAL PRIMARY KEY,
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    endpoint  TEXT NOT NULL,
    success   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_api_calls_called_at ON api_calls (called_at);
