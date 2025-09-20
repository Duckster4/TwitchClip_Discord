DROP TABLE IF EXISTS clips;

CREATE TABLE clips(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    clip_id TEXT UNIQUE,
    title TEXT,
    created_at TEXT,
    url TEXT,
    file_path TEXT,
    creator_id INTEGER,
    creator_name TEXT,
    is_featured BOOL,
    send BOOL
);