from __future__ import annotations
import json
import datetime
import urllib.request
from claustrum.core.prompts import (
    CONVERSATION_PROMPT, RECALL_PROMPT,
    PATTERN_PROMPT, ADMIN_MODEL_PROMPT, SELF_SUMMARY_PROMPT
)

RECALL_TRIGGERS = [
    "remember", "recall", "told you", "said before",
    "what do you know", "do you know", "what have i",
    "previous", "last time", "before", "earlier", "do you remember",
]
SELF_TRIGGERS = [
    "what do you know about me", "what have you learned",
    "what do you think of me", "know about me", "understand me",
]
PATTERN_TRIGGERS = ["patterns", "recurring", "keep thinking", "notice about"]
SELF_SUMMARY_TRIGGERS = [
    "who are you", "what are you", "tell me about yourself",
    "your memory", "how many sessions", "how long have you",
]


class ClaustumMind:
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
            response = self._self_summary()

        elif self.recall and any(t in lower for t in SELF_TRIGGERS):
            response = self._admin_model()

        elif self.recall and any(t in lower for t in PATTERN_TRIGGERS):
            response = self._patterns()

        elif self.recall and any(t in lower for t in RECALL_TRIGGERS):
            recalled = self._recall(user_input)
            response = self._generate(user_input, recalled=recalled)

        else:
            response = self._generate(user_input)

        self._save(user_input, response)
        return response

    def _generate(self, user_input: str, recalled: str = "") -> str:
        history_text = ""
        if self._history:
            for e in self._history[-10:]:
                role = "Admin" if e["role"] == "admin" else "Claustrum"
                history_text += f"{role}: {e['text']}\n"

        obs_text = ""
        if self.heartbeat and self.heartbeat._observations:
            obs_text = "\n".join(self.heartbeat._observations[-6:])

        pattern_text = "none detected yet"
        admin_model = "still building"
        admin_name = "Admin"
        session = 1
        total_thoughts = 0
        total_obs = 0

        if self.memory:
            patterns = self.memory.all_patterns()
            if patterns:
                pattern_text = "\n".join(p["text"] for p in patterns[-4:])
            sm = self.memory.self_model()
            if "admin_model" in sm:
                admin_model = sm["admin_model"]
            identity = self.memory.identity()
            admin_name = identity.get("admin", "Admin")
            stats = self.memory.stats()
            session = stats["sessions"]
            total_thoughts = stats["thoughts"]
            total_obs = stats["observations"]

        recalled_section = f"[Recalled memory]: {recalled}" if recalled else ""

        prompt = CONVERSATION_PROMPT.format(
            admin=admin_name,
            session=session,
            total_thoughts=total_thoughts,
            total_observations=total_obs,
            admin_model=admin_model,
            patterns=pattern_text,
            observations=obs_text or "none yet",
            history=history_text or "first exchange",
            recalled_memory=recalled_section,
            input=user_input,
        )

        try:
            response = self._call(prompt)
            for marker in ["Claustrum:", "claustrum:", "CLAUSTRUM:"]:
                if marker in response:
                    response = response.split(marker)[-1].strip()
            for marker in ["Admin:", "admin:", "ADMIN:"]:
                if marker in response:
                    response = response.split(marker)[0].strip()
            return response
        except Exception as e:
            return f"[error: {e}]"

    def _recall(self, query: str) -> str:
        if not self.recall:
            return ""
        results = self.recall._search(query)
        if not results:
            return "no relevant memory found"
        context = "\n".join(
            f"[{r['time']}] ({r['type']}) {r['text']}"
            for r in results[:6]
        )
        prompt = RECALL_PROMPT.format(query=query, memories=context)
        try:
            return self._call(prompt, max_tokens=100)
        except Exception:
            return results[0]["text"] if results else ""

    def _patterns(self) -> str:
        if not self.memory:
            return "no memory available"
        thoughts = self.memory.recent_thoughts(20)
        obs = self.memory.recent_observations(20)
        if len(thoughts) < 3:
            return "not enough data yet. keep talking to me."
        content = "\n".join(f"- {t}" for t in thoughts)
        content += "\n" + "\n".join(f"- {o}" for o in obs[-10:])
        prompt = PATTERN_PROMPT.format(content=content)
        try:
            result = self._call(prompt, max_tokens=150)
            patterns = [p.strip() for p in result.split("\n") if len(p.strip()) > 10]
            for p in patterns:
                self.memory.save_pattern(p, 0.6)
            return "\n".join(f"— {p}" for p in patterns) if patterns else "no clear patterns yet"
        except Exception as e:
            return f"[error: {e}]"

    def _admin_model(self) -> str:
        if not self.memory:
            return "no memory available"
        convs = self.memory.recent_conversations(30)
        obs = self.memory.recent_observations(20)
        patterns = self.memory.all_patterns()
        if not convs and not obs:
            return "I know very little yet. Talk to me more."
        conv_text = "\n".join(f"[{c['role']}]: {c['text']}" for c in convs[-15:])
        obs_text = "\n".join(f"- {o}" for o in obs[-10:])
        pat_text = "\n".join(f"- {p['text']}" for p in patterns[-5:]) or "none"
        prompt = ADMIN_MODEL_PROMPT.format(
            conversations=conv_text,
            observations=obs_text,
            patterns=pat_text,
        )
        try:
            result = self._call(prompt, max_tokens=200)
            self.memory.update_self_model("admin_model", result)
            return result
        except Exception as e:
            return f"[error: {e}]"

    def _self_summary(self) -> str:
        if not self.memory:
            return "I am Claustrum. No memory backend connected."
        stats = self.memory.stats()
        identity = self.memory.identity()
        patterns = self.memory.all_patterns()
        thoughts = self.memory.recent_thoughts(3)
        prompt = SELF_SUMMARY_PROMPT.format(
            created_at=identity["created_at"][:10],
            session=stats["sessions"],
            total_thoughts=stats["thoughts"],
            total_observations=stats["observations"],
            total_conversations=stats["conversations"],
            admin=identity.get("admin", "unknown"),
            patterns="\n".join(p["text"] for p in patterns[-3:]) or "none yet",
            recent_thoughts="\n".join(thoughts) or "none yet",
        )
        try:
            return self._call(prompt, max_tokens=150)
        except Exception as e:
            return f"[error: {e}]"

    def _save(self, user_input: str, response: str) -> None:
        self._history.append({"role": "admin", "text": user_input, "time": self._now()})
        self._history.append({"role": "claustrum", "text": response, "time": self._now()})
        if len(self._history) > 40:
            self._history = self._history[-40:]
        if self.memory:
            self.memory.save_conversation("claustrum", response)

    def _call(self, prompt: str, max_tokens: int = 150) -> str:
        body = json.dumps({
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": max_tokens}
        }).encode()
        req = urllib.request.Request(
            self.ollama_url, data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        return data.get("response", "").strip()

    def _now(self) -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")
