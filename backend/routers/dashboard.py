from fastapi import APIRouter, Depends, Query
from typing import Optional
from backend.db.crud import get_all_solicitations, get_all_profiles
from backend.database import get_connection
from backend.routers.auth import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MIN_SCORE = 0.40
MAX_PER_SECTION = 12


def get_agency_schedules():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM agency_release_schedule").fetchall()
    return [dict(r) for r in rows]


def _bulk_top_scores(profile_id: int, n: int = 3) -> dict:
    sql = """
        SELECT sc.solicitation_id, sc.score, c.name AS capability
        FROM solicitation_capability_scores sc
        JOIN capabilities c ON c.id = sc.capability_id
        WHERE c.profile_id = ?
        ORDER BY sc.solicitation_id, sc.score DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (profile_id,)).fetchall()

    result: dict = {}
    for row in rows:
        r = dict(row)
        sid = r["solicitation_id"]
        if sid not in result:
            result[sid] = []
        if len(result[sid]) < n:
            result[sid].append({"score": r["score"], "capability": r["capability"]})
    return result


def _score_color(score: float | None) -> str:
    if score is None or score == 0:
        return "gray"
    if score >= 0.7:
        return "green"
    if score >= 0.4:
        return "yellow"
    return "gray"


@router.get("")
def get_dashboard_summary(
    profile_id: Optional[int] = Query(None),
    user: dict | None = Depends(get_current_user),
):
    # Derive profiles to display scores for.
    # When a specific profile_id is requested (admin "viewing as" another user),
    # load that profile + shared profiles only — not the admin's own personal scores.
    # Otherwise show the current user's own profiles + shared profiles.
    user_id = user["id"] if user else None
    is_admin = user.get("is_admin") if user else False

    if profile_id and is_admin:
        all_profiles = get_all_profiles(include_all=True)
        profiles = [p for p in all_profiles if p["id"] == profile_id or p.get("shared")]
    else:
        profiles = get_all_profiles(user_id=user_id)

    # Fetch scores for display profiles only
    profile_score_maps = {
        p["id"]: {
            "name": p["name"],
            "map": _bulk_top_scores(p["id"]),
        }
        for p in profiles
    }

    # Determine primary sort profile
    if profile_id and any(p["id"] == profile_id for p in profiles):
        primary_id = str(profile_id)
    else:
        own_profile = next((p for p in profiles if not p.get("shared")), None)
        if own_profile and profile_score_maps.get(own_profile["id"], {}).get("map"):
            primary_id = str(own_profile["id"])
        else:
            shared_profile = next((p for p in profiles if p.get("shared")), None)
            fallback = shared_profile or own_profile or (profiles[0] if profiles else None)
            primary_id = str(fallback["id"]) if fallback else "1"

    solicitations = get_all_solicitations(
        limit=1000,
        exclude_expired=False,
        profile_id=primary_id,
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

        # Build per-profile score lists
        sol_profiles = []
        best = 0.0
        combined = 0.0
        for pid, pdata in profile_score_maps.items():
            scores = [s for s in pdata["map"].get(sol["id"], []) if s["score"] > 0]
            top = max((s["score"] for s in scores), default=0.0)
            if top > 0:
                sol_profiles.append({
                    "profile_id": pid,
                    "profile_name": pdata["name"],
                    "scores": scores,
                    "top": top,
                })
            best = max(best, top)
            combined += top

        if best < MIN_SCORE:
            continue

        sol["profile_scores"] = sol_profiles
        sol["score_color"] = _score_color(best)
        sol["best_score"] = best
        sol["combined_score"] = combined

        is_closed = bool(c_date and c_date < today_str)
        is_open = not is_closed and (not o_date or o_date <= today_str)
        in_tpoc = bool(
            not is_closed and not is_open
            and r_date and r_date <= today_str
            and o_date and o_date > today_str
        )

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

    def by_score(lst):
        return sorted(lst, key=lambda s: s.get("combined_score", 0), reverse=True)[:MAX_PER_SECTION]

    return {
        "tpoc_window": by_score(tpoc_window),
        "newly_released": by_score(newly_released),
        "open_now": by_score(open_now),
        "closing_soon": by_score(closing_soon),
        "recently_closed": by_score(recently_closed),
        "coming_soon": get_agency_schedules(),
        "profiles": [{"id": p["id"], "name": p["name"]} for p in profiles],
    }
