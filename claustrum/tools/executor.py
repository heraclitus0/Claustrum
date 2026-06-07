from __future__ import annotations
import json
import re
import urllib.request

TOOLS = {
    "code": "run Python code, math, or data algorithms",
    "file_read": "read local file contents",
    "file_write": "write/create local files",
    "file_list": "list files in a directory",
    "web_search": "search the web for current data",
    "calculate": "precise numerical calculation",
    "none": "no tool needed, regular conversation",
}


class ToolExecutor:
    """
    Decides tool routing for a request.
    Optimized for zero conversational filler and rapid local extraction.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/generate",
        ollama_model: str = "llama3.2",
        memory=None,
    ) -> None:
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.memory = memory

    def route(self, user_input: str) -> dict:
        """
        Determine tool assignment.
        Returns: {"tool": str, "plan": str, "needs_confirmation": bool}
        """
        tool_list = "\n".join(f"- {k}: {v}" for k, v in TOOLS.items())

        prompt = f"""Available Tools:\n{tool_list}\n\nUser Input: "{user_input}"\n\nTask: Select the single best tool for the input. Respond ONLY with a valid JSON object matching this schema exactly, with no explanation or markdown wrappers:\n{{"tool": "name_or_none", "plan": "1-sentence strategy description", "needs_confirmation": true_or_false}}"""

        try:
            body = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,    # Low temperature guarantees structural compliance
                    "num_predict": 96,     # Restricts unnecessary token rambling 
                    "num_ctx": 2048        # Limits runtime context overhead
                }
            }).encode()
            
            req = urllib.request.Request(
                self.ollama_url, data=body,
                headers={"Content-Type": "application/json"}
            )
            # 15 seconds max threshold protects the user interface from dropping on slow tool calls
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            
            response = data.get("response", "").strip()

            # Robust Regex Extraction: Catches raw JSON text even if the LLM wraps it in markdown text
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
                
            return json.loads(response)

        except Exception as e:
            # Safe programmatic fallback defaults to conversation instead of breaking the pipeline
            return {"tool": "none", "plan": f"Routing fallback (Error: {e})", "needs_confirmation": False}
