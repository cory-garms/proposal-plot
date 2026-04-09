"""
Nightly alignment scheduler.

Uses APScheduler (BackgroundScheduler) running inside the uvicorn process.
Default: runs at 02:00 server local time every night.

Config via environment:
  SCHEDULER_ENABLED=true        — enable/disable (default true)
  SCHEDULER_HOUR=2              — hour of day (0-23, default 2)
  SCHEDULER_MINUTE=0            — minute (default 0)

The scheduler shares _align_status with the capabilities router so the
Admin UI status card reflects scheduled runs the same as manual runs.
"""
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import SCHEDULER_ENABLED, SCHEDULER_HOUR, SCHEDULER_MINUTE

_scheduler: BackgroundScheduler | None = None


def _run_nightly_alignment() -> None:
    """Executed by APScheduler. Imports lazily to avoid circular imports."""
    from backend.capabilities.aligner import run_alignment
    from backend.routers.capabilities import _align_status

    if _align_status["running"]:
        print("[scheduler] Alignment already running — skipping scheduled run", file=sys.stderr)
        return

    print(f"[scheduler] Starting nightly alignment run", file=sys.stderr)
    _align_status["running"] = True
    _align_status["last_error"] = None
    try:
        stats = run_alignment(skip_scored=True, include_expired=False)
        _align_status["last_stats"] = stats
        print(f"[scheduler] Nightly alignment complete: {stats}", file=sys.stderr)
    except Exception as e:
        _align_status["last_error"] = str(e)
        print(f"[scheduler] Nightly alignment error: {e}", file=sys.stderr)
    finally:
        _align_status["running"] = False


def start_scheduler() -> None:
    global _scheduler
    if not SCHEDULER_ENABLED:
        print("[scheduler] Disabled (SCHEDULER_ENABLED=false)", file=sys.stderr)
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_nightly_alignment,
        trigger=CronTrigger(hour=SCHEDULER_HOUR, minute=SCHEDULER_MINUTE),
        id="nightly_alignment",
        name="Nightly capability alignment",
        replace_existing=True,
    )
    _scheduler.start()
    print(
        f"[scheduler] Nightly alignment scheduled at {SCHEDULER_HOUR:02d}:{SCHEDULER_MINUTE:02d} server time",
        file=sys.stderr,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_scheduler_info() -> dict:
    """Return schedule config for the /config endpoint."""
    if not SCHEDULER_ENABLED or _scheduler is None:
        return {"enabled": False}
    job = _scheduler.get_job("nightly_alignment")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "enabled": True,
        "hour": SCHEDULER_HOUR,
        "minute": SCHEDULER_MINUTE,
        "next_run": next_run,
    }
