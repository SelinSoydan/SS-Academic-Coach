import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "error_tracker.json"


class BugTracker:
    """Logs errors to logs/error_tracker.json and, if configured, to the Supabase bug_reports table."""

    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client

    def log(self, exc: Exception, context: str, severity: str = "error") -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "severity": severity,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        self._write_local(entry)
        self._write_remote(entry)
        return entry

    def _write_local(self, entry: dict) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        if LOG_PATH.exists():
            try:
                entries = json.loads(LOG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []
        entries.append(entry)
        LOG_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_remote(self, entry: dict) -> None:
        if self.supabase_client is None:
            return
        try:
            self.supabase_client.table("bug_reports").insert(entry).execute()
        except Exception:
            # Remote logging is best-effort; the local file is the source of truth.
            pass
