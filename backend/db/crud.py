import hashlib
import sqlite3
from typing import Optional
from backend.database import get_connection


def _content_hash(data: dict) -> str:
    """SHA-256 of title + description — used to detect unchanged solicitations."""
    text = (data.get("title") or "") + (data.get("description") or "")
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Solicitations
# ---------------------------------------------------------------------------

def upsert_solicitation(data: dict) -> int:
    """Insert or update a solicitation by URL. Returns the row id."""
    data = {**data, "content_hash": _content_hash(data)}
    sql = """
        INSERT INTO solicitations (agency, title, topic_number, description, deadline, open_date, close_date, release_date, vehicle_type, branch, tpoc_json, url, raw_html, source, content_hash)
        VALUES (:agency, :title, :topic_number, :description, :deadline, :open_date, :close_date, :release_date, :vehicle_type, :branch, :tpoc_json, :url, :raw_html, :source, :content_hash)
        ON CONFLICT(url) DO UPDATE SET
            agency       = excluded.agency,
            title        = excluded.title,
            topic_number = excluded.topic_number,
            description  = excluded.description,
            deadline     = excluded.deadline,
            open_date    = excluded.open_date,
            close_date   = excluded.close_date,
            release_date = excluded.release_date,
            vehicle_type = excluded.vehicle_type,
            branch       = excluded.branch,
            tpoc_json    = excluded.tpoc_json,
            raw_html     = excluded.raw_html,
            source       = excluded.source,
            content_hash = excluded.content_hash,
            scraped_at   = datetime('now')
    """
    with get_connection() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid




def get_all_solicitations(
    limit: int = 50,
    offset: int = 0,
    agency: Optional[str] = None,
    exclude_expired: bool = True,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    status_filter: Optional[str] = None,
    profile_id: Optional[str] = "1",
    watched_only: bool = False,
    source: Optional[str] = None,
) -> list[dict]:
    sql = """
        SELECT s.*, 
            (SELECT MAX(sc.score) FROM solicitation_capability_scores sc JOIN capabilities c ON c.id = sc.capability_id WHERE sc.solicitation_id = s.id AND c.profile_id = ?) as top_alignment_score,
            (SELECT c.name FROM solicitation_capability_scores sc JOIN capabilities c ON c.id = sc.capability_id WHERE sc.solicitation_id = s.id AND c.profile_id = ? ORDER BY sc.score DESC LIMIT 1) as top_capability
        FROM solicitations s
        WHERE 1=1
    """
    params: list = [profile_id, profile_id]

    if watched_only:
        sql += " AND s.watched = 1"

    if source:
        sql += " AND s.source = ?"
        params.append(source)

    if agency:
        sql += " AND s.agency = ?"
        params.append(agency)
        
    if exclude_expired and not status_filter == "expired":
        sql += " AND (IFNULL(s.close_date, s.deadline) IS NULL OR IFNULL(s.close_date, s.deadline) >= date('now'))"
        
    if status_filter == "tpoc":
        sql += " AND s.release_date IS NOT NULL AND IFNULL(s.open_date, s.release_date) > date('now') AND s.release_date <= date('now')"
    elif status_filter == "open":
        sql += " AND (IFNULL(s.close_date, s.deadline) IS NULL OR IFNULL(s.close_date, s.deadline) >= date('now')) AND (IFNULL(s.open_date, s.release_date) IS NULL OR IFNULL(s.open_date, s.release_date) <= date('now'))"
    elif status_filter == "closing":
        sql += " AND IFNULL(s.close_date, s.deadline) >= date('now') AND IFNULL(s.close_date, s.deadline) <= date('now', '+30 days')"
    elif status_filter == "expired":
        sql += " AND IFNULL(s.close_date, s.deadline) < date('now')"

    if sort_by == "alignment":
        sql += " ORDER BY top_alignment_score " + ("DESC" if sort_desc else "ASC") + " NULLS LAST"
    elif sort_by == "deadline":
        sql += " ORDER BY IFNULL(s.close_date, s.deadline) " + ("DESC" if sort_desc else "ASC") + " NULLS LAST"
    else:
        sql += " ORDER BY s.scraped_at DESC"
        
    sql += " LIMIT ? OFFSET ?"
    params += [limit, offset]
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_solicitation_by_id(solicitation_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM solicitations WHERE id = ?", (solicitation_id,)).fetchone()
    return dict(row) if row else None


def set_solicitation_watched(solicitation_id: int, watched: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE solicitations SET watched = ? WHERE id = ?",
            (1 if watched else 0, solicitation_id),
        )


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def get_all_profiles(user_id: Optional[int] = None, include_all: bool = False) -> list[dict]:
    """
    Return profiles visible to the given user:
      - include_all=True (admin): all profiles
      - user_id set: own profiles + shared profiles
      - user_id=None (unauthenticated): shared profiles only
    """
    if include_all:
        sql = "SELECT * FROM profiles ORDER BY name"
        params = []
    elif user_id is not None:
        sql = "SELECT * FROM profiles WHERE shared = 1 OR user_id = ? ORDER BY name"
        params = [user_id]
    else:
        sql = "SELECT * FROM profiles WHERE shared = 1 ORDER BY name"
        params = []
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_profile_by_id(profile_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return dict(row) if row else None


def insert_profile(name: str, user_id: Optional[int] = None, shared: bool = False) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO profiles (name, user_id, shared) VALUES (?, ?, ?)",
            (name, user_id, 1 if shared else 0),
        )
        return cur.lastrowid


def set_profile_shared(profile_id: int, shared: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE profiles SET shared = ? WHERE id = ?",
            (1 if shared else 0, profile_id),
        )

# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def get_all_capabilities(profile_id: Optional[int] = None) -> list[dict]:
    sql = "SELECT * FROM capabilities"
    params = []
    if profile_id:
        sql += " WHERE profile_id = ?"
        params.append(profile_id)
    sql += " ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def update_capability(capability_id: int, name: str, description: str, keywords_json: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE capabilities SET name = ?, description = ?, keywords_json = ? WHERE id = ?",
            (name, description, keywords_json, capability_id),
        )


def delete_capability(capability_id: int) -> None:
    with get_connection() as conn:
        # Remove scores first to avoid FK constraint violation
        conn.execute("DELETE FROM solicitation_capability_scores WHERE capability_id = ?", (capability_id,))
        conn.execute("DELETE FROM capabilities WHERE id = ?", (capability_id,))


def insert_capability(name: str, description: str, keywords_json: str, profile_id: int = 1) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO capabilities (profile_id, name, description, keywords_json) VALUES (?, ?, ?, ?) ON CONFLICT(profile_id, name) DO NOTHING",
            (profile_id, name, description, keywords_json),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------

def get_scored_pairs() -> set[tuple[int, int]]:
    """
    Return (solicitation_id, capability_id) pairs that have a non-zero score
    AND whose content hasn't changed since scoring (scored_hash matches current hash).
    Pairs with changed or missing hashes are excluded so they get re-scored.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT sc.solicitation_id, sc.capability_id
            FROM solicitation_capability_scores sc
            JOIN solicitations s ON s.id = sc.solicitation_id
            WHERE sc.score > 0
              AND sc.scored_hash IS NOT NULL
              AND sc.scored_hash = s.content_hash
        """).fetchall()
    return {(r["solicitation_id"], r["capability_id"]) for r in rows}


def upsert_score(solicitation_id: int, capability_id: int, score: float, rationale: str, content_hash: str = "") -> None:
    sql = """
        INSERT INTO solicitation_capability_scores (solicitation_id, capability_id, score, rationale, scored_hash)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(solicitation_id, capability_id) DO UPDATE SET
            score       = excluded.score,
            rationale   = excluded.rationale,
            scored_hash = excluded.scored_hash,
            scored_at   = datetime('now')
    """
    with get_connection() as conn:
        conn.execute(sql, (solicitation_id, capability_id, score, rationale, content_hash))


def get_scores_for_solicitation(solicitation_id: int, profile_id: Optional[int] = None) -> list[dict]:
    sql = """
        SELECT s.score, s.rationale, s.scored_at, c.name AS capability, c.id AS capability_id
        FROM solicitation_capability_scores s
        JOIN capabilities c ON c.id = s.capability_id
        WHERE s.solicitation_id = ?
    """
    params = [solicitation_id]
    if profile_id:
        sql += " AND c.profile_id = ?"
        params.append(profile_id)
        
    sql += " ORDER BY s.score DESC"
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
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


def get_draft_by_id(draft_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    return dict(row) if row else None


def update_draft_content(draft_id: int, content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE drafts SET content = ? WHERE id = ?",
            (content, draft_id),
        )


# ---------------------------------------------------------------------------
# Search Keywords
# ---------------------------------------------------------------------------

def get_all_keywords(active_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM search_keywords"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY keyword"
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def upsert_keyword(keyword: str, source: str = "manual") -> None:
    """Insert keyword if not present; never overwrites an existing row's source or active state."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO search_keywords (keyword, source) VALUES (?, ?)",
            (keyword.strip().lower(), source),
        )


def set_keyword_active(keyword_id: int, active: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE search_keywords SET active = ? WHERE id = ?",
            (1 if active else 0, keyword_id),
        )


def delete_keyword(keyword_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM search_keywords WHERE id = ?", (keyword_id,))
