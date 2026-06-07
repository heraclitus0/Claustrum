"""
Claustrum — an autonomous intelligence.
Observes, thinks, evolves.

Run: python run.py
"""
from __future__ import annotations
import pprint
import datetime
from claustrum.core.memory import ClaustumMemory
from claustrum.core.recall import ClaustumRecall
from claustrum.core.mind import ClaustumMind
from claustrum.core.heartbeat import Heartbeat


def main() -> None:
    print("=" * 60)
    print("  CLAUSTRUM")
    print("  autonomous intelligence")
    print("  persistent memory | active recall | pattern detection")
    print("=" * 60)
    print()
    print("  Talk to it naturally.")
    print("  It thinks on its own whether you talk or not.")
    print("  It remembers everything across sessions.")
    print()
    print("  'status'  — memory and system stats")
    print("  'exit'    — shut down cleanly")
    print()

    memory = ClaustumMemory()
    recall = ClaustumRecall(memory)
    hb = Heartbeat(interval_seconds=30, verbose=True, memory=memory)
    mind = ClaustumMind(heartbeat=hb, memory=memory, recall=recall)

    hb.start()
    hb.observe("Claustrum session started")

    try:
        while True:
            try:
                raw = input("\nyou> ").strip()
            except EOFError:
                break

            if not raw:
                continue

            if raw.lower() == "status":
                pprint.pprint(hb.status())
                continue

            if raw.lower() in ("exit", "quit", "stop"):
                hb.stop()
                break

            print("thinking...", end="\r")
            response = mind.respond(raw)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[CLAUSTRUM {ts}] {response}")

    except KeyboardInterrupt:
        hb.stop()
        print("\nClaustrum offline.")


if __name__ == "__main__":
    main()
