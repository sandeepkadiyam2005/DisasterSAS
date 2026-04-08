from __future__ import annotations

import logging
import os

from extensions import db
from models import WeatherLog
from services.reallocation_engine import rebalance_stuck_assignments

logger = logging.getLogger(__name__)
_scheduler_instance = None


def _cleanup_old_weather_logs():
    from datetime import datetime, timedelta

    threshold = datetime.utcnow() - timedelta(hours=72)
    stale_logs = WeatherLog.query.filter(WeatherLog.timestamp < threshold).all()
    count = len(stale_logs)
    for row in stale_logs:
        db.session.delete(row)
    if count:
        db.session.commit()
    logger.info("Scheduler cleanup complete: removed %s weather log(s)", count)


def _run_reallocator():
    report = rebalance_stuck_assignments(eta_threshold_minutes=180)
    if report.get("rebalanced_count"):
        db.session.commit()
    logger.info("Scheduler reallocator report: %s", report)


def start_background_scheduler(app):
    global _scheduler_instance
    if _scheduler_instance is not None:
        return _scheduler_instance

    enabled = os.environ.get("ENABLE_BACKGROUND_SCHEDULER", "true").lower() != "false"
    if not enabled:
        logger.info("Background scheduler disabled by ENABLE_BACKGROUND_SCHEDULER")
        return None

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception:
        logger.warning("APScheduler not installed. Background scheduler is disabled.")
        return None

    scheduler = BackgroundScheduler(timezone="UTC")

    def with_app_context(fn):
        def wrapped():
            with app.app_context():
                try:
                    fn()
                except Exception as exc:
                    logger.exception("Scheduled task failed: %s", exc)

        return wrapped

    scheduler.add_job(with_app_context(_cleanup_old_weather_logs), "interval", minutes=30, id="cleanup-weather")
    scheduler.add_job(with_app_context(_run_reallocator), "interval", minutes=5, id="rebalance-requests")
    scheduler.start()
    _scheduler_instance = scheduler
    logger.info("Background scheduler started")
    return scheduler
