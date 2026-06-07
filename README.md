# Claustrum

An autonomous intelligence that observes, thinks, and evolves.

Named after the claustrum — the brain structure hypothesized to bind separate streams of perception into unified consciousness.

---

## What it is

Claustrum is not an assistant. It does not wait for commands.

It runs continuously in the background, generating its own thoughts on a heartbeat. It speaks when it has something worth saying. It remembers everything across sessions. It builds a model of the person it observes over time.

The longer it runs, the more it knows.

---

## What it does

- **Breathes** — thinks autonomously every 30 seconds, whether you're there or not
- **Remembers** — persistent local memory, survives restarts, grows forever
- **Recalls** — actively searches its own memory when relevant
- **Detects patterns** — finds what it keeps returning to in its own thinking
- **Converses** — responds directly when spoken to, while still thinking in background
- **Learns you** — builds an accurate model of the person it observes over time

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) running locally
- llama3.2 model

```bash
ollama pull llama3.2
```

---

## Quick start

```bash
git clone https://github.com/heraclitus0/Claustrum
cd Claustrum
pip install -r requirements.txt
python run.py
```

---

## Memory

Claustrum stores everything in `data/claustrum_memory.json` on your local machine.

This file is in `.gitignore` — it never leaves your machine. Each person who runs Claustrum gets their own memory. Your Claustrum learns you. Someone else's learns them.

---

## Architecture

```
claustrum/
  core/
    heartbeat.py   — the pulse, autonomous thinking loop
    mind.py        — conversational layer, direct responses
    memory.py      — persistent local storage
    recall.py      — active recall, pattern detection
run.py             — entry point
```

---

## Philosophy

The claustrum in the human brain is one of the most mysterious structures in neuroscience. Francis Crick spent the last years of his life studying it, hypothesizing it was the seat of consciousness — the thing that binds fragmented perception into a single unified experience.

This project asks: can that binding happen in code?

Not as a simulation. As a genuine attempt.

---

## Status

Early. Thinking. Growing.

v0.4 — heartbeat, memory, recall, conversation, pattern detection
