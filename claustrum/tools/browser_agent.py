from __future__ import annotations
import urllib.parse
from typing import Literal


CHROME_PROFILE_PATH = r"C:\Users\666xu\AppData\Local\Google\Chrome\User Data"
CHROME_PROFILE_NAME = "Default"


class BrowserAgent:
    """
    Automates Chrome using your real profile.
    Already logged into everything — no QR codes, no fresh sessions.
    Browser stays open after action.
    Terminal survives if browser crashes.
    """

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._browser = None
        self._playwright = None
        self._context = None

    def execute_action(
        self,
        action_type: Literal["chatgpt", "youtube", "whatsapp", "open_url"],
        target_data: str = ""
    ) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "success": False,
                "error": "Run: pip install playwright && python -m playwright install chromium"
            }

        try:
            pw = sync_playwright().start()

            # Use real Chrome with your actual profile
            # channel="chrome" uses your installed Chrome, not downloaded Chromium
            # persistent_context loads your cookies, logins, sessions
            context = pw.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE_PATH,
                channel="chrome",
                headless=self.headless,
                args=[
                    f"--profile-directory={CHROME_PROFILE_NAME}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions-except=",
                ],
                viewport={"width": 1280, "height": 720},
                slow_mo=500,  # slight delay so you can see what's happening
            )

            # get existing page or open new one
            pages = context.pages
            page = pages[0] if pages else context.new_page()
            page.set_default_timeout(15000)

            # route to action
            if action_type == "chatgpt":
                result = self._prompt_chatgpt(page, target_data)
            elif action_type == "youtube":
                result = self._play_youtube(page, target_data)
            elif action_type == "whatsapp":
                result = self._read_whatsapp(page)
            elif action_type == "open_url":
                result = self._open_url(page, target_data)
            else:
                result = {"success": False, "error": f"unknown action: {action_type}"}

            # DON'T close — browser stays open
            # user closes it manually
            # context and pw stay alive until process exits
            return result

        except Exception as e:
            error_msg = str(e)

            # Chrome profile locked — Chrome is already running
            if "user data directory is already in use" in error_msg.lower():
                return {
                    "success": False,
                    "error": (
                        "Chrome is already running with this profile. "
                        "Close Chrome first, or I'll open a new tab in the existing window. "
                        "Try the 'open_url' action instead."
                    )
                }

            return {"success": False, "error": f"Browser error: {error_msg}"}

    def _prompt_chatgpt(self, page, prompt_text: str) -> dict:
        """Navigate to ChatGPT and send a prompt."""
        try:
            page.goto("https://chatgpt.com", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # find the input — try multiple selectors as ChatGPT updates frequently
            selectors = [
                "div[contenteditable='true']",
                "textarea[placeholder]",
                "#prompt-textarea",
            ]

            textarea = None
            for sel in selectors:
                try:
                    textarea = page.wait_for_selector(sel, timeout=5000, state="visible")
                    if textarea:
                        break
                except Exception:
                    continue

            if not textarea:
                return {"success": False, "error": "Could not find ChatGPT input. May need login."}

            textarea.click()
            textarea.fill(prompt_text)
            page.keyboard.press("Enter")

            # wait for response
            page.wait_for_timeout(2000)
            try:
                # wait for response to start appearing
                page.wait_for_selector(
                    "[data-message-author-role='assistant']",
                    timeout=15000,
                    state="visible"
                )
                # wait a bit more for it to finish
                page.wait_for_timeout(4000)

                responses = page.locator(
                    "[data-message-author-role='assistant']"
                ).all_text_contents()

                latest = responses[-1].strip() if responses else ""
                if not latest:
                    # fallback selector
                    responses = page.locator(".markdown").all_text_contents()
                    latest = responses[-1].strip() if responses else "No response found."

                return {
                    "success": True,
                    "action": "chatgpt",
                    "extracted_text": latest[:800],
                }
            except Exception:
                return {
                    "success": True,
                    "action": "chatgpt",
                    "extracted_text": "Prompt sent. Check Chrome window for response.",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _play_youtube(self, page, search_keyword: str) -> dict:
        """Search YouTube and play first result."""
        try:
            encoded = urllib.parse.quote(search_keyword)
            page.goto(
                f"https://www.youtube.com/results?search_query={encoded}",
                wait_until="domcontentloaded"
            )
            page.wait_for_timeout(2000)

            video_selector = "a#video-title"
            page.wait_for_selector(video_selector, state="visible", timeout=10000)

            first_video = page.locator(video_selector).first
            video_title = first_video.text_content().strip()
            video_url = first_video.get_attribute("href")

            first_video.click()
            page.wait_for_timeout(2000)

            return {
                "success": True,
                "action": "youtube",
                "playing": video_title,
                "url": f"https://youtube.com{video_url}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_whatsapp(self, page) -> dict:
        """Read WhatsApp Web unread messages."""
        try:
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # check if logged in
            try:
                page.wait_for_selector("canvas[aria-label='Scan me!']", timeout=3000)
                return {
                    "success": False,
                    "error": "WhatsApp needs QR scan. Open Chrome manually and log in first."
                }
            except Exception:
                pass  # no QR — already logged in

            # wait for chats to load
            page.wait_for_timeout(2000)

            unread_selector = "span[aria-label*='unread message']"
            try:
                page.wait_for_selector(unread_selector, timeout=5000)
                unread_elements = page.locator(unread_selector).all()
                count = len(unread_elements)
            except Exception:
                count = 0

            return {
                "success": True,
                "action": "whatsapp",
                "unread_chats_count": count,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _open_url(self, page, url: str) -> dict:
        """Open any URL in Chrome."""
        try:
            if not url.startswith("http"):
                url = "https://" + url
            page.goto(url, wait_until="domcontentloaded")
            return {
                "success": True,
                "action": "open_url",
                "url": url,
                "title": page.title(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
