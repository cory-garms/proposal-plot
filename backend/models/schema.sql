CREATE TABLE IF NOT EXISTS solicitations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agency      TEXT NOT NULL,
    title       TEXT NOT NULL,
    topic_number TEXT,
    description TEXT,
    deadline    TEXT,
    url         TEXT UNIQUE,
    raw_html    TEXT,
    scraped_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS capabilities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    keywords_json TEXT NOT NULL DEFAULT '[]'
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

CREATE INDEX IF NOT EXISTS idx_solicitations_agency   ON solicitations(agency);
CREATE INDEX IF NOT EXISTS idx_solicitations_deadline ON solicitations(deadline);
CREATE INDEX IF NOT EXISTS idx_projects_solicitation  ON projects(solicitation_id);
CREATE INDEX IF NOT EXISTS idx_drafts_project         ON drafts(project_id);
CREATE INDEX IF NOT EXISTS idx_scores_solicitation    ON solicitation_capability_scores(solicitation_id);
