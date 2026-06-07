"""
Claustrum — autonomous intelligence with tools.
Run: python run.py
"""
from __future__ import annotations
import pprint
import datetime
from claustrum.core.memory import ClaustumMemory
from claustrum.core.recall import ClaustumRecall
from claustrum.core.mind import ClaustumMind
from claustrum.core.heartbeat import Heartbeat
from claustrum.tools.executor import ToolExecutor
from claustrum.tools.code_runner import CodeRunner
from claustrum.tools.files import FileOps
from claustrum.tools.web_search import WebSearch
from claustrum.tools.browser_agent import BrowserAgent # <-- IMPORT THE NEW AGENT


def handle_tool(
    tool: str, 
    plan: str, 
    user_input: str, 
    executor, 
    runner, 
    files, 
    search, 
    browser,          # <-- Added to routing signature
    routing_data: dict # <-- Added to safely parse sub-keys
) -> str:
    """Show plan, get confirmation, execute."""

    print(f"\n[CLAUSTRUM] I'll {plan}")
    print(f"[CLAUSTRUM] Tool: {tool}")

    if tool == "code":
        print("\ngenerating code...", end="\r")
        code = runner.generate_code(user_input)
        print(f"\n--- code ---\n{code}\n--- end ---")
        confirm = input("\nexecute this? (y/n) > ").strip().lower()
        if confirm == "y":
            print("running...", end="\r")
            result = runner.run_code(code)
            if result["success"]:
                return f"Done.\n{result['output']}" if result["output"] else "Done. No output."
            else:
                return f"Error: {result['error']}"
        return "cancelled."

    elif tool == "file_read":
        path = user_input.replace("read", "").replace("open", "").replace("show", "").strip()
        if not path:
            path = input("path > ").strip()
        confirm = input(f"\nread {path}? (y/n) > ").strip().lower()
        if confirm == "y":
            result = files.read(path)
            if result["success"]:
                content = result["content"]
                if len(content) > 2000:
                    content = content[:2000] + f"\n... [{len(result['content'])-2000} more chars]"
                return content
            return f"Error: {result['error']}"
        return "cancelled."

    elif tool == "file_write":
        path = input("save to path > ").strip()
        print("generating content...", end="\r")
        code = runner.generate_code(f"Generate content for: {user_input}\nPrint only the final content, nothing else.")
        result_preview = runner.run_code(code)
        content = result_preview["output"] if result_preview["success"] else user_input
        print(f"\n--- content preview ---\n{content[:500]}{'...' if len(content)>500 else ''}\n---")
        confirm = input(f"\nwrite to {path}? (y/n) > ").strip().lower()
        if confirm == "y":
            result = files.write(path, content)
            if result["success"]:
                return f"Written to {result['path']} ({result['bytes_written']} bytes)."
            return f"Error: {result['error']}"
        return "cancelled."

    elif tool == "file_list":
        path = user_input.replace("list", "").replace("show", "").replace("files", "").replace("in", "").strip()
        if not path:
            path = input("directory path > ").strip()
        confirm = input(f"\nlist {path}? (y/n) > ").strip().lower()
        if confirm == "y":
            result = files.list_dir(path)
            if result["success"]:
                lines = []
                for e in result["entries"][:30]:
                    icon = "📁" if e["type"] == "dir" else "📄"
                    size = f" ({e['size']} bytes)" if e.get("size") else ""
                    lines.append(f"{icon} {e['name']}{size}")
                return "\n".join(lines)
            return f"Error: {result['error']}"
        return "cancelled."

    elif tool == "web_search":
        query = user_input.replace("search", "").replace("look up", "").replace("find", "").strip()
        confirm = input(f"\nsearch for '{query}'? (y/n) > ").strip().lower()
        if confirm == "y":
            print("searching...", end="\r")
            result = search.search(query)
            if result["success"]:
                lines = []
                for r in result["results"][:3]:
                    lines.append(f"[{r['source']}] {r['text']}")
                    if r["url"]:
                        lines.append(f"  → {r['url']}")
                return "\n".join(lines)
            return f"No results: {result.get('error', 'unknown error')}"
        return "cancelled."

    elif tool == "calculate":
        print(f"\n--- will calculate ---\n{user_input}\n---")
        confirm = input("\nrun? (y/n) > ").strip().lower()
        if confirm == "y":
            result = runner.run_code(
                f"import math\nresult = {user_input}\nprint(result)"
            )
            if result["success"]:
                return result["output"]
            return f"Error: {result['error']}"
        return "cancelled."

    # NEW: Handle browser automation commands
    elif tool == "browser_chrome":
        action_type = routing_data.get("action_type", "none")
        target_data = routing_data.get("target_data", "")
        
        print(f"\n[TARGET ACTION] Target platform: {action_type}")
        if target_data:
            print(f"[DATA PAYLOAD] Action payload: {target_data}")
            
        confirm = input(f"\nLaunch Chrome and execute {action_type}? (y/n) > ").strip().lower()
        if confirm == "y":
            print("Automating browser window...", end="\r")
            result = browser.execute_action(action_type, target_data)
            if result["success"]:
                # Print explicit formatted output structures based on the execution result fields
                if action_type == "chatgpt":
                    return f"ChatGPT Output Scraped successfully:\n{result['extracted_text']}"
                elif action_type == "youtube":
                    return f"Now Playing on YouTube: {result['playing']}\nURL: {result['url']}"
                elif action_type == "whatsapp":
                    return f"WhatsApp notification summary collected. Unread threads count: {result['unread_chats_count']}"
            return f"Automation Error: {result.get('error', 'Unknown UI extraction failure')}"
        return "cancelled."

    return "I don't know how to handle that tool."


def main() -> None:
    print("=" * 60)
    print("  CLAUSTRUM")
    print("  autonomous intelligence + agent tools")
    print("=" * 60)
    print()
    print("  Talk naturally. Ask it to do things.")
    print("  It always shows what it plans before doing it.")
    print("  'status' — stats  |  'exit' — quit")
    print()

    memory = ClaustumMemory()
    recall = ClaustumRecall(memory)
    hb = Heartbeat(interval_seconds=30, verbose=True, memory=memory)
    mind = ClaustumMind(heartbeat=hb, memory=memory, recall=recall)
    executor = ToolExecutor(memory=memory)
    runner = CodeRunner()
    files = FileOps()
    search = WebSearch()
    browser = BrowserAgent(headless=False) # <-- Initialize here (headless=False keeps the browser window visible on your laptop screen)

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

            # route: tool or conversation?
            print("thinking...", end="\r")
            routing = executor.route(raw)
            tool = routing.get("tool", "none")
            plan = routing.get("plan", "")

            ts = datetime.datetime.now().strftime("%H:%M:%S")

            if tool != "none":
                # Passed routing and browser tracking contexts directly down to tool handler
                result = handle_tool(tool, plan, raw, executor, runner, files, search, browser, routing)
                print(f"[CLAUSTRUM {ts}] {result}")
                if memory:
                    memory.save_observation(f"used tool '{tool}' for: {raw}")
            else:
                response = mind.respond(raw)
                print(f"[CLAUSTRUM {ts}] {response}")

    except KeyboardInterrupt:
        hb.stop()
        print("\nClaustrum offline.")


if __name__ == "__main__":
    main()
