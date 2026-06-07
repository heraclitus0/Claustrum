from __future__ import annotations
import threading
import time
import datetime
import json
import urllib.request
from typing import Callable
from claustrum.core.prompts import HEARTBEAT_PROMPT


class Heartbeat:
    def __init__(
        self,
        interval_seconds: int = 30,
        on_tick: Callable[[], None] | None = None,
        on_tap: Callable[[str], None] | None = None,
        verbose: bool = True,
        ollama_url: str = "http://localhost:11434/api/generate",
        ollama_model: str = "llama3.2",
        memory=None,
    ) -> None:
        self.interval = interval_seconds
        self.on_tick = on_tick
        self.on_tap = on_tap
        self.verbose = verbose
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.memory = memory

        self._running = False
        self._thread: threading.Thread | None = None
        self._tick_count = 0
        self._started_at: float | None = None
        self._speak_every = 3
        self._pattern_every = 15

        self._observations: list[str] = []
        self._last_thoughts: list[str] = []

        if self.memory:
            # Drop lookback limits from 20/5 to 10/3 to shrink the input prompt token size
            self._observations = list(self.memory.recent_observations(10))
            self._last_thoughts = list(self.memory.recent_thoughts(3))

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._started_at = time.time()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="claustrum-heartbeat"
        )
        self._thread.start()

        if self.memory:
            session = self.memory.increment_session()
            stats = self.memory.stats()
            if session == 1:
                msg = "online. session 1. no prior memory."
            else:
                msg = (
                    f"online. session {session}. "
                    f"{stats['observations']} observations, "
                    f"{stats['thoughts']} thoughts."
                )
        else:
            msg = "online."
        self._print_tap(msg)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.memory:
            stats = self.memory.stats()
            self._print_tap(f"offline. {stats['thoughts']} thoughts total.")
        else:
            self._print_tap("offline.")

    def is_alive(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def uptime(self) -> str:
        if not self._started_at:
            return "not started"
        s = int(time.time() - self._started_at)
        return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

    def observe(self, text: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M")
        self._observations.append(f"[{ts}] {text}")
        if len(self._observations) > 15:
            self._observations = self._observations[-15:]
        if self.memory:
            self.memory.save_observation(text)

    def status(self) -> dict:
        base = {
            "alive": self.is_alive(),
            "ticks": self._tick_count,
            "uptime": self.uptime(),
            "interval": self.interval,
            "model": self.ollama_model,
        }
        if self.memory:
            base["memory"] = self.memory.stats()
        return base

    def _loop(self) -> None:
        while self._running:
            time.sleep(self.interval)
            if not self._running:
                break
            try:
                self._tick()
            except Exception as e:
                self._print_tap(f"loop tick error: {e}")

    def _tick(self) -> None:
        self._tick_count += 1
        if self.on_tick:
            try:
                self.on_tick()
            except Exception as e:
                self._print_tap(f"tick callback error: {e}")

        if self._tick_count % self._speak_every == 0:
            thought = self._generate_thought()
            if thought and not thought.startswith("["):
                self._last_thoughts.append(thought)
                if len(self._last_thoughts) > 5:
                    self._last_thoughts = self._last_thoughts[-5:]
                if self.memory:
                    self.memory.save_thought(thought, self._tick_count)
                self._print_tap(thought)
                if self.on_tap:
                    self.on_tap(thought)

        if self._tick_count % self._pattern_every == 0 and self.memory:
            self._detect_patterns()

    def _generate_thought(self) -> str:
        admin = "Admin"
        session = 1
        total = 0
        patterns = "none"

        if self.memory:
            identity = self.memory.identity()
            admin = identity.get("admin", "Admin")
            session = self.memory.session_count()
            total = self.memory.stats()["thoughts"]
            p = self.memory.all_patterns()
            if p:
                patterns = "\n".join(x["text"] for x in p[-2:])

        obs = "\n".join(self._observations[-5:]) or "none"
        thoughts = "\n".join(self._last_thoughts[-2:]) or "none"

        prompt = HEARTBEAT_PROMPT.format(
            admin=admin,
            session=session,
            total_thoughts=total,
            time=datetime.datetime.now().strftime("%H:%M on %A"),
            uptime=self.uptime(),
            patterns=patterns,
            observations=obs,
            recent_thoughts=thoughts,
        )

        try:
            body = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7, 
                    "num_predict": 64,   
                    "num_ctx": 2048,    
                    "top_k": 20,
                    "top_p": 0.9
                }
            }).encode()
            
            req = urllib.request.Request(
                self.ollama_url, data=body,
                headers={"Content-Type": "application/json"}
            )
      
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read())
            
            res = data.get("response", "").strip()
            if res.lower() in ["[silent]", "silent", ""]:
                return "[silent]"
            return res
        except Exception as e:
            return f"[timeout/error: {e}]"

    def _detect_patterns(self) -> None:
        try:
            from claustrum.core.recall import ClaustumRecall
            recall = ClaustumRecall(self.memory, self.ollama_url, self.ollama_model)
            patterns = recall.detect_patterns()
            if patterns:
                self._print_tap(f"pattern: {patterns[0]}")
        except Exception:
            pass

    def _print_tap(self, message: str) -> None:
        if self.verbose:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"\n[CLAUSTRUM {ts}] {message}", flush=True)
