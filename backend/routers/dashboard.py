from fastapi import APIRouter
from backend.db.crud import get_all_solicitations
from backend.database import get_connection
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def get_agency_schedules():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM agency_release_schedule").fetchall()
    return [dict(r) for r in rows]

@router.get("")
def get_dashboard_summary():
    # We fetch all solicitations to categorize them.
    # We do not exclude expired for this view because we want to see "Recently closed".
    solicitations = get_all_solicitations(limit=1000, exclude_expired=False)
    
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

        # Exclude ancient history altogether
        if c_date and c_date < sixty_days_ago:
            continue
            
        is_closed = bool(c_date and c_date < today_str)
        is_open = not is_closed and (not o_date or o_date <= today_str)
        in_tpoc = bool(not is_closed and not is_open and r_date and r_date <= today_str and o_date and o_date > today_str)

        if is_closed and c_date >= sixty_days_ago:
            recently_closed.append(sol)
        
        if not is_closed:
            if o_date and o_date >= two_weeks_ago and o_date <= today_str:
                newly_released.append(sol)
            if in_tpoc:
                tpoc_window.append(sol)
            if is_open:
                open_now.append(sol)
            if c_date and c_date <= thirty_days_from_now:
                closing_soon.append(sol)

    schedules = get_agency_schedules()

    return {
        "tpoc_window": tpoc_window,
        "newly_released": newly_released,
        "open_now": open_now,
        "closing_soon": closing_soon,
        "recently_closed": recently_closed,
        "coming_soon": schedules, 
    }
