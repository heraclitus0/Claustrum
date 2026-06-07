from __future__ import annotations
import json
import datetime
import urllib.request


class ClaustumRecall:
    """
    Active memory awareness for Claustrum.
    Optimized to eliminate blocking delays on local hardware layouts.
    """

    def __init__(
        self,
        memory,
        ollama_url: str = "http://localhost:11434/api/generate",
        ollama_model: str = "llama3.2",
    ) -> None:
        self.memory = memory
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model

    def self_summary(self) -> str:
        stats = self.memory.stats()
        identity = self.memory.identity()
        patterns = self.memory.all_patterns()
        recent_thoughts = self.memory.recent_thoughts(2) 

        lines = [
            f"I am Claustrum. First online: {identity['created_at'][:10]}.",
            f"This is session {stats['sessions']}.",
            f"I have recorded {stats['thoughts']} autonomous thoughts, "
            f"{stats['observations']} observations, "
            f"{stats['conversations']} conversation exchanges.",
        ]

        admin = identity.get("admin", "unknown")
        if admin != "unknown":
            lines.append(f"My admin is {admin}.")

        if patterns:
            lines.append(f"Detected patterns ({len(patterns)}):")
            for p in patterns[-2:]: 
                lines.append(f"  — {p['text']}")

        if recent_thoughts:
            lines.append("Recent thoughts:")
            for t in recent_thoughts:
                lines.append(f"  — {t}")

        return "\n".join(lines)

    def recall(self, query: str) -> str:
        results = self._search(query)
        if not results:
            return f"No stored memory relevant to '{query}'."

        context = "\n".join(
            f"[{r['time']}] ({r['type']}) {r['text']}"
            for r in results[:4]
        )

        prompt = f"""You are Claustrum extracting memories for: {query}
Stored Context:\n{context}

Task: Summarize relevant details in 1-2 sentences using first-person ("I remember"). Be factual and specific to the data. Output ONLY the summary."""

        try:
            return self._call_ollama(prompt, max_tokens=64)
        except Exception:
            return "\n".join(f"[{r['time']}] {r['text']}" for r in results[:3])

    def detect_patterns(self) -> list[str]:
        thoughts = self.memory.recent_thoughts(12)
        if len(thoughts) < 3:
            return []

        thought_text = "\n".join(f"- {t}" for t in thoughts)

        prompt = f"""You are Claustrum detecting human thought patterns.
Thoughts:\n{thought_text}

Task: Identify 2 recurring behavioral themes. One sentence per pattern. No numbers or intro remarks. Output ONLY the raw patterns."""

        try:
            response = self._call_ollama(prompt, max_tokens=64)
            patterns = [p.strip() for p in response.split("\n") if len(p.strip()) > 10]
            for pattern in patterns[:2]:
                self.memory.save_pattern(pattern, confidence=0.6)
            return patterns
        except Exception:
            return []

    def what_do_i_know_about_admin(self) -> str:
        conversations = self.memory.recent_conversations(15)
        observations = self.memory.recent_observations(10)
        patterns = self.memory.all_patterns()

        if not conversations and not observations:
            return "I know very little about my admin yet. Still observing."

        conv_text = "\n".join(f"[{c['role']}]: {c['text']}" for c in conversations[-8:])
        obs_text = "\n".join(f"- {o}" for o in observations[-6:])
        pattern_text = "\n".join(f"- {p['text']}" for p in patterns[-2:])

        prompt = f"""You are Claustrum profile tracking your admin.
Convos:\n{conv_text}
Observations:\n{obs_text}
Patterns:\n{pattern_text if pattern_text else "none"}

Task: Provide an honest, accurate assessment of your admin in 3 sentences. Focus on habits and contradictions. Output ONLY the assessment."""

        try:
            result = self._call_ollama(prompt, max_tokens=128)
            self.memory.update_self_model("admin_model", result)
            return result
        except Exception as e:
            return f"[recall profiling error: {e}]"

    def _search(self, query: str) -> list[dict]:
        query_words = set(query.lower().split())
        results = []

        for obs in self.memory._data.get("observations", []):
            score = self._score(obs["text"], query_words)
            if score > 0:
                results.append({"type": "observation", "time": obs["time"],
                                 "text": obs["text"], "score": score})

        for thought in self.memory._data.get("thoughts", []):
            score = self._score(thought["text"], query_words)
            if score > 0:
                results.append({"type": "thought", "time": thought["time"],
                                 "text": thought["text"], "score": score})

        for conv in self.memory._data.get("conversations", []):
            score = self._score(conv["text"], query_words)
            if score > 0:
                results.append({"type": f"conversation ({conv['role']})",
                                 "time": conv["time"], "text": conv["text"],
                                 "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _score(self, text: str, query_words: set) -> int:
        return len(query_words & set(text.lower().split()))

    def _call_ollama(self, prompt: str, max_tokens: int = 64) -> str:
        body = json.dumps({
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.6, 
                "num_predict": max_tokens, 
                "num_ctx": 2048 
            }
        }).encode()
        req = urllib.request.Request(
            self.ollama_url, data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read())
        return data.get("response", "").strip()
