import sqlite3
from typing import Optional
from backend.database import get_connection


# ---------------------------------------------------------------------------
# Solicitations
# ---------------------------------------------------------------------------

def upsert_solicitation(data: dict) -> int:
    """Insert or update a solicitation by URL. Returns the row id."""
    sql = """
        INSERT INTO solicitations (agency, title, topic_number, description, deadline, url, raw_html)
        VALUES (:agency, :title, :topic_number, :description, :deadline, :url, :raw_html)
        ON CONFLICT(url) DO UPDATE SET
            agency       = excluded.agency,
            title        = excluded.title,
            topic_number = excluded.topic_number,
            description  = excluded.description,
            deadline     = excluded.deadline,
            raw_html     = excluded.raw_html,
            scraped_at   = datetime('now')
    """
    with get_connection() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def get_all_solicitations(limit: int = 50, offset: int = 0, agency: Optional[str] = None) -> list[dict]:
    sql = "SELECT * FROM solicitations"
    params: list = []
    if agency:
        sql += " WHERE agency = ?"
        params.append(agency)
    sql += " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_solicitation_by_id(solicitation_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM solicitations WHERE id = ?", (solicitation_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def get_all_capabilities() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM capabilities ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def insert_capability(name: str, description: str, keywords_json: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO capabilities (name, description, keywords_json) VALUES (?, ?, ?)",
            (name, description, keywords_json),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------

def upsert_score(solicitation_id: int, capability_id: int, score: float, rationale: str) -> None:
    sql = """
        INSERT INTO solicitation_capability_scores (solicitation_id, capability_id, score, rationale)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(solicitation_id, capability_id) DO UPDATE SET
            score     = excluded.score,
            rationale = excluded.rationale,
            scored_at = datetime('now')
    """
    with get_connection() as conn:
        conn.execute(sql, (solicitation_id, capability_id, score, rationale))


def get_scores_for_solicitation(solicitation_id: int) -> list[dict]:
    sql = """
        SELECT s.score, s.rationale, s.scored_at, c.name AS capability, c.id AS capability_id
        FROM solicitation_capability_scores s
        JOIN capabilities c ON c.id = s.capability_id
        WHERE s.solicitation_id = ?
        ORDER BY s.score DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (solicitation_id,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def insert_project(solicitation_id: int, title: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO projects (solicitation_id, title) VALUES (?, ?)",
            (solicitation_id, title),
        )
        return cur.lastrowid


def get_project_by_id(project_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Drafts
# ---------------------------------------------------------------------------

def insert_draft(project_id: int, section_type: str, content: str, model_version: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO drafts (project_id, section_type, content, model_version) VALUES (?, ?, ?, ?)",
            (project_id, section_type, content, model_version),
        )
        return cur.lastrowid


def get_drafts_for_project(project_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM drafts WHERE project_id = ? ORDER BY generated_at DESC",
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]
