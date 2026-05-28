CREATE TABLE IF NOT EXISTS panel_users (
    discord_id       BIGINT PRIMARY KEY,
    discord_name     TEXT NOT NULL,
    is_admin         BOOLEAN NOT NULL DEFAULT FALSE,
    can_view_logs    BOOLEAN NOT NULL DEFAULT TRUE,
    can_control_bots BOOLEAN NOT NULL DEFAULT FALSE,
    can_fetch_api    BOOLEAN NOT NULL DEFAULT FALSE
);
