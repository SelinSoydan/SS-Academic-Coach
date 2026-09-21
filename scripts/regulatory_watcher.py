"""Daily check for new SPK duyuru / Resmi Gazete items.

Fetches the configured source pages, diffs titles against the last snapshot
stored in Supabase (`regulatory_updates` table), and inserts anything new.
Never fabricates data: a failed fetch is logged via BugTracker and the job
exits without writing placeholder rows.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client

SOURCES = [
    {"name": "SPK Duyurular", "url": "https://spk.gov.tr/duyurular"},
    {"name": "Resmi Gazete", "url": "https://www.resmigazete.gov.tr/"},
]


def fetch_titles(url: str) -> list[str]:
    resp = requests.get(url, timeout=15, headers={"User-Agent": "ss-academic-coach-watcher/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.find_all("a")
    return sorted({a.get_text(strip=True) for a in links if a.get_text(strip=True)})


def run() -> None:
    client = get_supabase_client()
    tracker = BugTracker(supabase_client=client)

    if client is None:
        print("Supabase yapılandırılmamış (SUPABASE_URL/SUPABASE_KEY eksik). Çalıştırılamadı.")
        return

    known = {
        row["title"] for row in client.table("regulatory_updates").select("title").execute().data
    }

    for source in SOURCES:
        try:
            titles = fetch_titles(source["url"])
        except Exception as exc:
            tracker.log(exc, context=f"regulatory_watcher:{source['name']}")
            continue

        new_titles = [t for t in titles if t not in known]
        for title in new_titles:
            client.table("regulatory_updates").insert(
                {
                    "title": title,
                    "source": source["name"],
                    "source_url": source["url"],
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()

        print(f"{source['name']}: {len(new_titles)} yeni öğe eklendi.")


if __name__ == "__main__":
    run()
