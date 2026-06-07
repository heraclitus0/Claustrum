from __future__ import annotations
import json
import re
import urllib.request
from typing import Literal

class BrowserAgent:
    """
    Automates local browser interactions (ChatGPT, YouTube, WhatsApp).
    Designed with tight execution boundaries to prevent local thread hangs.
    """
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless

    def execute_action(self, action_type: Literal["chatgpt", "youtube", "whatsapp"], target_data: str) -> dict:
        """
        Routes and executes local browser automations dynamically.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"success": False, "error": "Dependency missing. Run: pip install playwright"}

        try:
            with sync_playwright() as p:
                # Launching with a short 10s network timeout threshold
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(viewport={"width": 1280, "height": 720})
                page = context.new_page()
                page.set_default_timeout(10000) 

                if action_type == "chatgpt":
                    return self._prompt_chatgpt(page, target_data)
                elif action_type == "youtube":
                    return self._play_youtube(page, target_data)
                elif action_type == "whatsapp":
                    return self._read_whatsapp(page)
                
                browser.close()
        except Exception as e:
            return {"success": False, "error": f"Browser automation failed: {e}"}

    def _prompt_chatgpt(self, page, prompt_text: str) -> dict:
        """Opens ChatGPT, injects a prompt, and scrapes the response context."""
        page.goto("https://chatgpt.com")
        # Locate the standard text area input
        textarea = page.wait_for_selector("textarea", state="visible")
        textarea.fill(prompt_text)
        page.keyboard.press("Enter")
        
        # Wait safely for the response stream to complete generating
        page.wait_for_selector(".markdown", state="visible")
        page.wait_for_timeout(4000) # Quick buffer for short answers
        
        # Pull the last response generated on the screen
        responses = page.locator(".markdown").all_text_contents()
        latest_reply = responses[-1].strip() if responses else "No response text found."
        
        return {"success": True, "action": "chatgpt", "extracted_text": latest_reply[:500]}

    def _play_youtube(self, page, search_keyword: str) -> dict:
        """Opens YouTube, searches for a video topic, and clicks the first result."""
        encoded = urllib.parse.quote(search_keyword)
        page.goto(f"https://www.youtube.com/results?search_query={encoded}")
        
        # Select and click the first organic video thumbnail rendering element
        video_selector = "a#video-title"
        page.wait_for_selector(video_selector, state="visible")
        first_video = page.locator(video_selector).first
        video_title = first_video.text_content().strip()
        video_url = first_video.get_attribute("href")
        
        # Actually click the element to load the video on your desktop browser
        first_video.click()
        page.wait_for_timeout(3000) # Keep browser open to initiate playback buffer
        
        return {"success": True, "action": "youtube", "playing": video_title, "url": f"https://youtube.com{video_url}"}

    def _read_whatsapp(self, page) -> dict:
        """Loads WhatsApp Web to scan unread text notifications."""
        page.goto("https://web.whatsapp.com")
        
        # Note: Requires a pre-authenticated browser profile session to skip QR login loops
        unread_selector = "span[aria-label*='unread message']"
        try:
            page.wait_for_selector(unread_selector, timeout=5000)
            unread_elements = page.locator(unread_selector).all()
            return {"success": True, "action": "whatsapp", "unread_chats_count": len(unread_elements)}
        except Exception:
            return {"success": True, "action": "whatsapp", "unread_chats_count": 0, "status": "No unread alerts or login required."}
