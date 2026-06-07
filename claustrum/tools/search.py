from __future__ import annotations
import urllib.request
import urllib.parse
import json


class WebSearch:
    """
    Search the web using DuckDuckGo instant answers API.
    Optimized to safeguard the background runtime thread against network hanging.
    """

    def search(self, query: str) -> dict:
        try:
            # Clean and trim the query to improve API resolution speeds
            clean_query = " ".join(query.strip().split()[:6])
            encoded = urllib.parse.quote(clean_query)
            
            # Appended explicit parameters to force direct string answers over heavy nesting
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1&no_redirect=1"
            
            # Masked the agent header as a standard browser client to stop silent rate-limit drops
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                }
            )
            
            # Dropped explicit connection block timeout from 10s to a crisp 6s
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))

            results = []

            # 1. Capture primary abstract direct definitions
            if data.get("AbstractText"):
                results.append({
                    "source": data.get("AbstractSource", "DDG Abstract"),
                    "text": data["AbstractText"].strip(),
                    "url": data.get("AbstractURL", ""),
                })

            # 2. Extract nested relative topics safely without crashing on sub-arrays
            related_topics = data.get("RelatedTopics", [])
            topic_count = 0
            
            for topic in related_topics:
                if topic_count >= 2:  # Bounded item limit prevents prompt context bloat
                    break
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "source": "DDG Topic",
                        "text": topic["Text"].strip(),
                        "url": topic.get("FirstURL", ""),
                    })
                    topic_count += 1

            if not results:
                return {
                    "success": False,
                    "query": query,
                    "error": "No instant summary results found.",
                }

            return {
                "success": True,
                "query": query,
                "results": results,
            }
            
        except Exception as e:
            # Safe programmatic fallback isolation prevents parent pipeline loops from freezing
            return {"success": False, "query": query, "error": f"Network error: {e}"}
