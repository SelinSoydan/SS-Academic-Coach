"""Takım Masası: uygulamayı aynı anda açık tutan herkesin gördüğü ortak, canlı durum.

st.cache_resource sunucu belleğinde tek bir nesne tutar ve bütün oturumlar aynı nesneyi paylaşır.
Uygulama yeniden başlarsa pano sıfırlanır; bu yüzden JSON olarak dışa ve içe aktarılabilir.
Kalıcı kayıt için bir sonraki adım aynı arayüzü Supabase tablosuna bağlamak.
"""
import copy
import datetime
import json
import threading

import streamlit as st


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class TeamBoard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.data = {"votes": {}, "members": {}, "scores": {}, "scenarios": []}

    def vote(self, name: str, call: str, target: float, thesis: str, risk: str) -> None:
        with self._lock:
            self.data["votes"][name] = {"call": call, "target": float(target), "thesis": thesis, "risk": risk, "ts": _now()}

    def set_member(self, name: str, role: str, sections: list) -> None:
        with self._lock:
            self.data["members"][name] = {"role": role, "sections": list(sections), "ts": _now()}

    def record_score(self, name: str, correct: int, total: int) -> None:
        with self._lock:
            best = self.data["scores"].get(name, {}).get("best", 0)
            self.data["scores"][name] = {"last": correct, "total": total, "best": max(best, correct), "ts": _now()}

    def save_scenario(self, name: str, author: str, url: str, summary: str) -> None:
        with self._lock:
            self.data["scenarios"].insert(0, {"name": name, "author": author, "url": url, "summary": summary, "ts": _now()})
            del self.data["scenarios"][20:]

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self.data)

    def export_json(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2)

    def load(self, payload: dict) -> None:
        with self._lock:
            for key in ("votes", "members", "scores", "scenarios"):
                if key in payload:
                    self.data[key] = copy.deepcopy(payload[key])


@st.cache_resource
def get_board() -> TeamBoard:
    return TeamBoard()
