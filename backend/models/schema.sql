CREATE TABLE IF NOT EXISTS solicitations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agency      TEXT NOT NULL,
    title       TEXT NOT NULL,
    topic_number TEXT,
    description TEXT,
    deadline    TEXT,
    open_date   TEXT,
    close_date  TEXT,
    release_date TEXT,
    vehicle_type TEXT NOT NULL DEFAULT 'SBIR',  -- SBIR, STTR, BAA, OTA, Grant
    branch       TEXT,                          -- DOD sub-component: Army, Navy, Air Force, etc.
    tpoc_json    TEXT,                          -- JSON array of {name, email} TPOC contacts
    watched      INTEGER NOT NULL DEFAULT 0,
    url         TEXT UNIQUE,
    raw_html    TEXT,
    source      TEXT DEFAULT 'sbir',               -- 'sbir', 'grants', 'sam'
    scraped_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    is_admin        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    user_id     INTEGER REFERENCES users(id),
    shared      INTEGER NOT NULL DEFAULT 0   -- 1 = visible to all authenticated users
);

CREATE TABLE IF NOT EXISTS capabilities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  INTEGER NOT NULL DEFAULT 1 REFERENCES profiles(id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(profile_id, name)
);

CREATE TABLE IF NOT EXISTS agency_release_schedule (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agency      TEXT NOT NULL,
    solicitation_cycle TEXT NOT NULL,
    expected_release_month TEXT NOT NULL,
    expected_open_month TEXT NOT NULL,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitation_id INTEGER NOT NULL REFERENCES solicitations(id),
    title           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drafts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(id),
    section_type  TEXT NOT NULL,
    content       TEXT NOT NULL,
    model_version TEXT NOT NULL,
    generated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS solicitation_capability_scores (
    solicitation_id INTEGER NOT NULL REFERENCES solicitations(id),
    capability_id   INTEGER NOT NULL REFERENCES capabilities(id),
    score           REAL NOT NULL,
    rationale       TEXT,
    scored_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (solicitation_id, capability_id)
);

CREATE TABLE IF NOT EXISTS search_keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword     TEXT NOT NULL UNIQUE,
    source      TEXT NOT NULL DEFAULT 'manual',  -- 'capability', 'csv', 'manual'
    active      INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sota_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitation_id INTEGER NOT NULL REFERENCES solicitations(id),
    query           TEXT NOT NULL,
    papers_json     TEXT NOT NULL,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_solicitations_agency   ON solicitations(agency);
CREATE INDEX IF NOT EXISTS idx_solicitations_deadline ON solicitations(deadline);
CREATE INDEX IF NOT EXISTS idx_projects_solicitation  ON projects(solicitation_id);
CREATE INDEX IF NOT EXISTS idx_drafts_project         ON drafts(project_id);
CREATE INDEX IF NOT EXISTS idx_scores_solicitation    ON solicitation_capability_scores(solicitation_id);
CREATE INDEX IF NOT EXISTS idx_search_keywords_active ON search_keywords(active);
CREATE INDEX IF NOT EXISTS idx_sota_cache_solicitation ON sota_cache(solicitation_id);
