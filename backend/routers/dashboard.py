from fastapi import APIRouter, Query
from backend.db.crud import get_all_solicitations
from backend.database import get_connection
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_agency_schedules():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM agency_release_schedule").fetchall()
    return [dict(r) for r in rows]


def _top_scores(solicitation_id: int, profile_id: str, n: int = 3) -> list[dict]:
    """Return the top-n capability scores for a solicitation under a given profile."""
    sql = """
        SELECT sc.score, c.name AS capability
        FROM solicitation_capability_scores sc
        JOIN capabilities c ON c.id = sc.capability_id
        WHERE sc.solicitation_id = ? AND c.profile_id = ?
        ORDER BY sc.score DESC
        LIMIT ?
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (solicitation_id, profile_id, n)).fetchall()
    return [dict(r) for r in rows]


def _score_color(score: float | None) -> str:
    if score is None or score == 0:
        return "gray"
    if score >= 0.7:
        return "green"
    if score >= 0.4:
        return "yellow"
    return "gray"


@router.get("")
def get_dashboard_summary(profile_id: str = Query("1")):
    solicitations = get_all_solicitations(
        limit=1000,
        exclude_expired=False,
        profile_id=profile_id,
    )

    today = datetime.now()
    two_weeks_ago = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    sixty_days_ago = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    thirty_days_from_now = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    newly_released = []
    tpoc_window = []
    open_now = []
    closing_soon = []
    recently_closed = []

    for sol in solicitations:
        c_date = sol.get("close_date") or sol.get("deadline")
        o_date = sol.get("open_date") or sol.get("release_date")
        r_date = sol.get("release_date")

        if c_date and c_date < sixty_days_ago:
            continue

        is_closed = bool(c_date and c_date < today_str)
        is_open = not is_closed and (not o_date or o_date <= today_str)
        in_tpoc = bool(
            not is_closed and not is_open
            and r_date and r_date <= today_str
            and o_date and o_date > today_str
        )

        # Attach top-3 scores and color signal
        top = _top_scores(sol["id"], profile_id, n=3)
        sol["top_scores"] = top
        sol["score_color"] = _score_color(sol.get("top_alignment_score"))

        if is_closed and c_date >= sixty_days_ago:
            recently_closed.append(sol)

        if not is_closed:
            if o_date and two_weeks_ago <= o_date <= today_str:
                newly_released.append(sol)
            if in_tpoc:
                tpoc_window.append(sol)
            if is_open:
                open_now.append(sol)
            if c_date and c_date <= thirty_days_from_now:
                closing_soon.append(sol)

    # Sort every section by alignment score descending (unscored to bottom)
    def by_score(lst):
        return sorted(lst, key=lambda s: s.get("top_alignment_score") or 0, reverse=True)

    schedules = get_agency_schedules()

    return {
        "tpoc_window": by_score(tpoc_window),
        "newly_released": by_score(newly_released),
        "open_now": by_score(open_now),
        "closing_soon": by_score(closing_soon),
        "recently_closed": by_score(recently_closed),
        "coming_soon": schedules,
    }
