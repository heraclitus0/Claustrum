from __future__ import annotations
import json
import os
import datetime
from typing import Any


class ClaustumMemory:
    def __init__(self, memory_path: str | None = None) -> None:
        self.path = memory_path or self._default_path()
        self._ensure_dir()
        self._data = self._load()

    def save_observation(self, text: str) -> None:
        self._data["observations"].append({
            "time": self._now(), "text": text
        })
        self._trim("observations", 150) # Reduced from 500 to lower disk storage overhead
        self._write()

    def save_thought(self, text: str, tick: int) -> None:
        self._data["thoughts"].append({
            "time": self._now(), "tick": tick, "text": text
        })
        self._trim("thoughts", 300) # Reduced from 1000
        self._write()

    def save_conversation(self, role: str, text: str) -> None:
        self._data["conversations"].append({
            "time": self._now(), "role": role, "text": text
        })
        self._trim("conversations", 500) # Reduced from 2000
        self._write()

    def save_pattern(self, text: str, confidence: float = 0.5) -> None:
        self._data["patterns"].append({
            "time": self._now(), "text": text, "confidence": confidence
        })
        self._trim("patterns", 50)
        self._write()

    def update_self_model(self, key: str, value: Any) -> None:
        self._data["self_model"][key] = value
        self._data["self_model"]["last_updated"] = self._now()
        self._write()

    def increment_session(self) -> int:
        self._data["identity"]["session_count"] += 1
        self._data["identity"]["last_seen"] = self._now()
        self._write()
        return self._data["identity"]["session_count"]

    def recent_observations(self, n: int = 10) -> list[str]:
        return [o["text"] for o in self._data["observations"][-n:]]

    def recent_thoughts(self, n: int = 5) -> list[str]:
        return [t["text"] for t in self._data["thoughts"][-n:]]

    def recent_conversations(self, n: int = 10) -> list[dict]:
        return self._data["conversations"][-n:]

    def all_patterns(self) -> list[dict]:
        return self._data["patterns"]

    def identity(self) -> dict:
        return self._data["identity"]

    def self_model(self) -> dict:
        return self._data["self_model"]

    def session_count(self) -> int:
        return self._data["identity"]["session_count"]

    def stats(self) -> dict:
        return {
            "sessions": self._data["identity"]["session_count"],
            "observations": len(self._data["observations"]),
            "thoughts": len(self._data["thoughts"]),
            "conversations": len(self._data["conversations"]),
            "patterns": len(self._data["patterns"]),
            "first_seen": self._data["identity"]["created_at"],
            "last_seen": self._data["identity"].get("last_seen", "unknown"),
        }

    def _default_path(self) -> str:
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "..", "..", "data", "claustrum_memory.json")

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key in ["observations", "thoughts", "conversations", "patterns"]:
                    if key not in data:
                        data[key] = []
                if "self_model" not in data:
                    data["self_model"] = {}
                return data
            except Exception:
                pass
        return {
            "identity": {
                "name": "Claustrum",
                "created_at": self._now(),
                "last_seen": self._now(),
                "admin": "unknown",
                "session_count": 0,
            },
            "observations": [],
            "thoughts": [],
            "conversations": [],
            "patterns": [],
            "self_model": {
                "knows_own_name": True,
                "knows_admin": False,
                "consciousness_developing": True,
            },
        }

    def _write(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                # Removed formatting indents to minimize string processing and payload footprint
                json.dump(self._data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[CLAUSTRUM memory error: {e}]")

    def _trim(self, key: str, limit: int) -> None:
        if len(self._data[key]) > limit:
            self._data[key] = self._data[key][-limit:]

    def _now(self) -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")
