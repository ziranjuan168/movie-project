from __future__ import annotations

import atexit
import threading

from .services import sync_now_playing


_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def start_scheduler(app) -> None:
    global _scheduler_thread

    if (
        _scheduler_thread is not None and _scheduler_thread.is_alive()
    ) or not app.config.get("AUTO_SYNC_ENABLED", True):
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(app,),
        name="douban-sync",
        daemon=True,
    )
    _scheduler_thread.start()
    atexit.register(_shutdown_scheduler)


def _scheduler_loop(app) -> None:
    interval_seconds = max(int(app.config["SYNC_INTERVAL_HOURS"] * 3600), 60)
    while not _stop_event.is_set():
        with app.app_context():
            try:
                result = sync_now_playing(city=app.config["DOUBAN_CITY"])
                app.logger.info(
                    "douban sync finished: fetched=%s created=%s refreshed=%s deactivated=%s",
                    result.fetched,
                    result.created,
                    result.refreshed,
                    result.deactivated,
                )
            except Exception as exc:  # pragma: no cover - log side effect
                app.logger.exception("douban sync failed: %s", exc)

        if _stop_event.wait(timeout=interval_seconds):
            break


def _shutdown_scheduler() -> None:
    global _scheduler_thread
    _stop_event.set()
    _scheduler_thread = None
