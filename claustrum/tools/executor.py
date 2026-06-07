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
    "browser_chrome": "open browser to use chatgpt, play youtube videos, or read whatsapp texts",
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
        Returns: {"tool": str, "action_type": str, "target_data": str, "plan": str, "needs_confirmation": bool}
        """
        tool_list = "\n".join(f"- {k}: {v}" for k, v in TOOLS.items())

        # Updated prompt schema containing browser payload instructions
        prompt = f"""Available Tools:\n{tool_list}

User Input: "{user_input}"

Task: Select the single best tool. If browser actions are required, use "browser_chrome". Respond ONLY with a valid JSON object matching this schema exactly, with no explanation or markdown wrappers:
{{"tool": "tool_name_or_none", "action_type": "chatgpt_or_youtube_or_whatsapp_or_none", "target_data": "prompt_text_or_search_keyword_or_empty", "plan": "1-sentence strategy description", "needs_confirmation": true_or_false}}"""

        try:
            body = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,    # Low temperature guarantees structural compliance
                    "num_predict": 128,    # Slightly increased to comfortably accommodate extra schema strings
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
            return {
                "tool": "none", 
                "action_type": "none", 
                "target_data": "", 
                "plan": f"Routing fallback (Error: {e})", 
                "needs_confirmation": False
            }
