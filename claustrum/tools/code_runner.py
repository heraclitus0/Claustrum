from __future__ import annotations
import subprocess
import sys
import tempfile
import os
import json
import re
import urllib.request


class CodeRunner:
    """
    Generates and executes code scripts.
    Optimized to eliminate syntax-scraping errors and local hardware strain.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/generate",
        ollama_model: str = "llama3.2",
    ) -> None:
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model

    def generate_code(self, task: str) -> str:
        """Generate optimized Python code for a given task."""
        
        prompt = f"""Task: Write a clean, complete Python script to execute the following requirements:
"{task}"

Rules:
- Print results explicitly using print().
- Wrap all logical steps in basic try-except blocks to handle exceptions gracefully.
- Output ONLY the valid executable Python code. No introductory remarks, no explanations."""

        try:
            body = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,    # 0.0 ensures strict syntax tracking and cuts hallucinated parameters
                    "num_predict": 300,    # Slashed from 500 to optimize throughput latency
                    "num_ctx": 2048        # Caps background context window memory growth
                }
            }).encode()
            
            req = urllib.request.Request(
                self.ollama_url, data=body,
                headers={"Content-Type": "application/json"}
            )
            # Tightened timeout limit prevents your parent app from hanging permanently on slow model cycles
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            code = data.get("response", "").strip()

            # Robust Regex Parsing: Extracts the python block even if the model violates rules and uses markdown code blocks
            match = re.search(r"```(?:python)?\s*(.*?)\s*
```", code, re.DOTALL)
            if match:
                return match.group(1).strip()
                
            return code
            
        except Exception as e:
            return f"print('[Generation Failure: {e}]')"

    def run_code(self, code: str) -> dict:
        """
        Execute Python code safely in an isolated subprocess block.
        Returns: {"success": bool, "output": str, "error": str, "code": str}
        """
        # Return early if generation stage failed out programmatically
        if "Generation Failure" in code:
            return {"success": False, "output": "", "error": code, "code": code}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=15, # Lowered from 30s to keep thread execution responsive
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "code": code,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Execution timed out after 15 seconds.",
                "code": code,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "code": code,
            }
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
