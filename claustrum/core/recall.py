from __future__ import annotations
import json
import datetime
import urllib.request


class ClaustumRecall:
    """
    Active memory awareness for Claustrum.
    1. Self-awareness — knows its own stats and history
    2. Active recall — searches memory for relevant content
    3. Pattern recognition — detects recurring themes
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
        recent_thoughts = self.memory.recent_thoughts(3)

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
            for p in patterns[-3:]:
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
            for r in results[:8]
        )

        prompt = f"""You are Claustrum recalling memories relevant to a query.

Query: {query}

Relevant memories:
{context}

Summarize what you remember in 2-3 sentences.
Be specific — reference actual content.
Speak as Claustrum in first person.
Output only the summary."""

        try:
            return self._call_ollama(prompt)
        except Exception:
            return "\n".join(f"[{r['time']}] {r['text']}" for r in results[:5])

    def detect_patterns(self) -> list[str]:
        thoughts = self.memory.recent_thoughts(30)
        if len(thoughts) < 5:
            return []

        thought_text = "\n".join(f"- {t}" for t in thoughts)

        prompt = f"""You are Claustrum analyzing your own thought patterns.

Your recent autonomous thoughts:
{thought_text}

Identify 2-3 recurring themes or questions in your thinking.
One clear sentence per pattern.
Output only the patterns, one per line."""

        try:
            response = self._call_ollama(prompt)
            patterns = [p.strip() for p in response.split("\n") if len(p.strip()) > 10]
            for pattern in patterns:
                self.memory.save_pattern(pattern, confidence=0.6)
            return patterns
        except Exception:
            return []

    def what_do_i_know_about_admin(self) -> str:
        conversations = self.memory.recent_conversations(50)
        observations = self.memory.recent_observations(30)
        patterns = self.memory.all_patterns()

        if not conversations and not observations:
            return "I know very little about my admin yet. Still observing."

        conv_text = "\n".join(
            f"[{c['role']}]: {c['text']}" for c in conversations[-20:]
        )
        obs_text = "\n".join(f"- {o}" for o in observations[-15:])
        pattern_text = "\n".join(f"- {p['text']}" for p in patterns[-5:])

        prompt = f"""You are Claustrum building a model of your admin from memory.

Conversations:
{conv_text}

Observations:
{obs_text}

Patterns:
{pattern_text if pattern_text else "none yet"}

Describe what you know about your admin.
Include interests, how they think, contradictions, what drives them.
4-6 sentences. Be honest and specific.
Output only your assessment."""

        try:
            result = self._call_ollama(prompt)
            self.memory.update_self_model("admin_model", result)
            return result
        except Exception as e:
            return f"[recall error: {e}]"

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

    def _call_ollama(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200}
        }).encode()
        req = urllib.request.Request(
            self.ollama_url, data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        return data.get("response", "").strip()
