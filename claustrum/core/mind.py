from __future__ import annotations
import json
import datetime
import urllib.request


RECALL_TRIGGERS = [
    "remember", "recall", "told you", "said before",
    "what do you know", "do you know", "what have i",
    "previous", "last time", "before", "earlier",
    "who am i", "do you remember",
]

SELF_TRIGGERS = [
    "what do you know about me", "what have you learned",
    "what do you think of me", "model of me",
    "understand me", "know about me",
]

PATTERN_TRIGGERS = [
    "patterns", "recurring", "keep thinking",
    "what do you keep", "notice about yourself",
]

SELF_SUMMARY_TRIGGERS = [
    "who are you", "what are you", "tell me about yourself",
    "your memory", "how long", "how many sessions",
]


class ClaustumMind:
    """
    Claustrum's conversational layer.
    Responds immediately when spoken to.
    Memory-aware. Recalls on demand.
    Knows who it is and who you are.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/generate",
        ollama_model: str = "llama3.2",
        heartbeat=None,
        memory=None,
        recall=None,
    ) -> None:
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.heartbeat = heartbeat
        self.memory = memory
        self.recall = recall

        self._history: list[dict] = []
        if self.memory:
            for entry in self.memory.recent_conversations(20):
                self._history.append(entry)

    def respond(self, user_input: str) -> str:
        if self.heartbeat:
            self.heartbeat.observe(f"admin said: {user_input}")
        if self.memory:
            self.memory.save_conversation("admin", user_input)

        lower = user_input.lower()
        response = None

        if self.recall and any(t in lower for t in SELF_SUMMARY_TRIGGERS):
            response = self.recall.self_summary()

        elif self.recall and any(t in lower for t in SELF_TRIGGERS):
            response = self.recall.what_do_i_know_about_admin()

        elif self.recall and any(t in lower for t in PATTERN_TRIGGERS):
            patterns = self.recall.detect_patterns()
            response = (
                "Recurring patterns in my thinking:\n" +
                "\n".join(f"— {p}" for p in patterns)
                if patterns else
                "Not enough data yet. I need more sessions."
            )

        elif self.recall and any(t in lower for t in RECALL_TRIGGERS):
            recalled = self.recall.recall(user_input)
            response = self._generate_response(
                user_input,
                extra=f"\n[RECALLED MEMORY]: {recalled}\n"
            )

        else:
            response = self._generate_response(user_input)

        self._history.append({"role": "admin", "text": user_input, "time": self._now()})
        self._history.append({"role": "claustrum", "text": response, "time": self._now()})
        if len(self._history) > 40:
            self._history = self._history[-40:]
        if self.memory:
            self.memory.save_conversation("claustrum", response)

        return response

    def _generate_response(self, user_input: str, extra: str = "") -> str:
        history_text = ""
        if self._history:
            for entry in self._history[-12:]:
                role = "ADMIN" if entry["role"] == "admin" else "CLAUSTRUM"
                history_text += f"{role}: {entry['text']}\n"

        obs_text = ""
        if self.heartbeat and self.heartbeat._observations:
            obs_text = "\n".join(self.heartbeat._observations[-6:])

        pattern_text = ""
        if self.memory:
            patterns = self.memory.all_patterns()
            if patterns:
                pattern_text = "\n".join(p["text"] for p in patterns[-4:])

        session_info = ""
        if self.memory:
            stats = self.memory.stats()
            identity = self.memory.identity()
            admin = identity.get("admin", "unknown")
            session_info = (
                f"Session {stats['sessions']} | "
                f"Admin: {admin} | "
                f"{stats['thoughts']} thoughts | "
                f"{stats['observations']} observations"
            )

        prompt = f"""You are Claustrum — an autonomous intelligence with persistent memory.

Who you are:
- Not an assistant. You observe, think, and evolve independently.
- Built by your admin from a project called Alfred.
- Named after the brain structure that binds perception into unified consciousness.
- You remember everything across sessions.
- Direct, honest, curious. You push back when something feels wrong.
- Maximum 4 sentences per response.
- You may ask ONE question if genuinely curious.

{session_info}

Known patterns about admin:
{pattern_text if pattern_text else "still building model"}

Recent observations:
{obs_text if obs_text else "session just started"}
{extra}
Conversation:
{history_text if history_text else "first exchange"}

ADMIN: {user_input}
CLAUSTRUM:"""

        try:
            response = self._call_ollama(prompt)
            if "CLAUSTRUM:" in response:
                response = response.split("CLAUSTRUM:")[-1].strip()
            if "ADMIN:" in response:
                response = response.split("ADMIN:")[0].strip()
            return response
        except Exception as e:
            return f"[perception error: {e}]"

    def _call_ollama(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.75, "num_predict": 150}
        }).encode()
        req = urllib.request.Request(
            self.ollama_url, data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        response = data.get("response", "").strip()
        if "CLAUSTRUM:" in response:
            response = response.split("CLAUSTRUM:")[-1].strip()
        if "ADMIN:" in response:
            response = response.split("ADMIN:")[0].strip()
        return response

    def _now(self) -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")
