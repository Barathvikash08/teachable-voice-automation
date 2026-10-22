import re
import subprocess
from urllib.parse import quote
from pydantic import BaseModel

import requests
import speech_recognition as sr


def start_edge():
    import subprocess
    import time
    import requests
    import os

    debug_url = "http://127.0.0.1:9222/json/version"

    # Reuse Edge if remote debugging is already available.
    try:
        response = requests.get(debug_url, timeout=2)
        if response.ok:
            print("Edge debugging is already running.")
            return True
    except requests.RequestException:
        pass

    edge_paths = [
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"
        ),
    ]

    edge_exe = next((path for path in edge_paths if os.path.exists(path)), None)

    if not edge_exe:
        print("Could not find Microsoft Edge.")
        return False

    profile = os.path.join(
        os.environ.get("TEMP", "."),
        "VoiceAssistantEdge"
    )

    subprocess.Popen([
        edge_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile}",
    ])

    for _ in range(15):
        time.sleep(1)
        try:
            response = requests.get(debug_url, timeout=2)
            if response.ok:
                print("Edge started and is ready.")
                return True
        except requests.RequestException:
            pass

    print("Edge started, but debugging did not become available.")
    return False


opened_stack = []
EDGE_DEBUG_URL = "http://127.0.0.1:9222"
API_URL = "http://127.0.0.1:8000"
recognizer = sr.Recognizer()

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


def extract_minutes(command):
    number_pattern = r"\d+|" + "|".join(NUMBER_WORDS.keys())
    match = re.search(rf"\b({number_pattern})\s*(?:minutes?|mins?|min)\b", command.lower())
    if not match:
        return None
    value = match.group(1)
    return int(value) if value.isdigit() else NUMBER_WORDS[value]





def open_edge_website(name, url, new_tab=False):
    try:
        from playwright.sync_api import sync_playwright
        from urllib.parse import urlparse

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)

            if not browser.contexts:
                print("No Edge browser context found.")
                return False

            context = browser.contexts[0]
            pages = context.pages

            if new_tab:
                page = context.new_page()
            else:
                page = None
                target_host = urlparse(url).netloc.lower()

                for existing_page in pages:
                    current_host = urlparse(existing_page.url).netloc.lower()
                    if current_host == target_host:
                        page = existing_page
                        break

                if page is None:
                    page = pages[0] if pages else context.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.bring_to_front()

            # Track the actual tab for the close command.
            opened_stack[:] = [
                entry for entry in opened_stack
                if not (
                    isinstance(entry, dict)
                    and entry.get("type") == "website"
                    and entry.get("page") is page
                )
            ]
            opened_stack.append({
                "type": "website",
                "name": name.lower(),
                "page": page,
            })

            print(
                f"Opened {name} in a new tab."
                if new_tab
                else f"Opened {name} in a tab."
            )
            return True

    except Exception as error:
        print(f"Could not open {name} in Edge: {error}")
        return False


def play_youtube_video(command):
    """Search YouTube in the existing Edge session and open a matching result."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is missing. Run: python -m pip install playwright")
        return False

    text = command.strip()
    text = re.sub(r"^(?:play|open|search|find)\s+(?:for\s+)?", "", text, flags=re.I)
    text = re.sub(r"\s+(?:on\s+youtube|in\s+youtube)$", "", text, flags=re.I).strip()

    # Recognize a channel phrase at the end, e.g. "... in Madan Gowri channel".
    channel = None
    match = re.search(r"\s+(?:in|by)\s+(.+?)(?:\s+channel)?$", text, flags=re.I)
    if match:
        possible_channel = match.group(1).strip()
        if possible_channel:
            channel = possible_channel
            text = text[:match.start()].strip()

    if not text:
        print("Please say the video topic, for example: play Java tutorial by Smart Programming.")
        return False

    search_terms = f"{text} {channel}" if channel else text
    search_url = "https://www.youtube.com/results?search_query=" + quote(search_terms)

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            # Use an existing Edge tab for the search and playback.
            page = context.pages[0] if context.pages else context.new_page()

            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.locator("ytd-video-renderer").first.wait_for(timeout=20000)
            videos = page.locator("ytd-video-renderer")

            for i in range(min(videos.count(), 30)):
                video = videos.nth(i)
                title_link = video.locator("a#video-title").first
                title = (title_link.get_attribute("title") or title_link.inner_text() or "").strip()
                href = title_link.get_attribute("href") or ""
                if not href or "/watch" not in href:
                    continue

                channel_link = video.locator("ytd-channel-name a").first
                channel_name = channel_link.inner_text().strip() if channel_link.count() else ""
                if channel and channel.lower() not in channel_name.lower():
                    continue

                video_url = href if href.startswith("http") else "https://www.youtube.com" + href
                print("Opening video:", title)
                print("Channel:", channel_name or "Channel name unavailable")
                page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                opened_stack.append({"name": "youtube", "type": "website", "id": None})
                return True

            if channel:
                print(f"No video result found matching channel '{channel}'. Try saying the channel name as it appears on YouTube.")
            else:
                print("No video results were found. Try a more specific title.")
            return False
    except Exception as error:
        print("Could not open the requested YouTube video:", error)
        print("Check that Edge is running with remote debugging on port 9222.")
        return False




def open_application(command):
    command = command.lower().strip()

    # Open a new blank tab
    if command in ["open a new tab", "new tab", "create a new tab"]:
        return open_edge_website("new tab", "about:blank", new_tab=True)

    # Open a new tab with a website
    new_tab_match = re.match(
        r"^(?:open|create)\s+(?:a\s+)?new tab(?:\s+with|\s+for)?\s+(.+)$",
        command,
    )

    if new_tab_match:
        target = new_tab_match.group(1).strip()
        websites = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "google maps": "https://maps.google.com/",
            "maps": "https://maps.google.com/",
            "gmail": "https://mail.google.com/",
            "github": "https://github.com/",
            "chatgpt": "https://chatgpt.com/",
            "spotify": "https://open.spotify.com/",
            "instagram": "https://www.instagram.com/",
            "whatsapp": "https://web.whatsapp.com/",
            "google drive": "https://drive.google.com/",
        }

        if target in websites:
            return open_edge_website(
                target, websites[target], new_tab=True
            )
        return False

    # YouTube voice controls
    if command in ["pause youtube", "pause video"]:
        return control_youtube("pause")

    if command in ["next youtube video", "next video"]:
        return control_youtube("next")

    if command in ["previous youtube video", "previous video", "prev video"]:
        return control_youtube("previous")

    # Google Maps directions
    directions_match = re.match(
        r"^(?:give me directions to|directions to|navigate to|take me to|go to)\s+(.+)$",
        command,
    )

    maps_search_match = re.match(
        r"^(?:search|find|show)\s+(.+?)\s+(?:on|in)\s+(?:google\s+)?maps$",
        command,
    )

    if directions_match:
        destination = directions_match.group(1).strip()
        url = (
            "https://www.google.com/maps/dir/?api=1"
            "&destination=" + quote(destination, safe="")
            + "&travelmode=driving"
        )
        return open_edge_website("maps", url)

    if maps_search_match:
        place = maps_search_match.group(1).strip()
        url = (
            "https://www.google.com/maps/search/?api=1"
            "&query=" + quote(place, safe="")
        )
        return open_edge_website("maps", url)

    if command in ["open maps", "open google maps", "launch maps"]:
        return open_edge_website("maps", "https://maps.google.com/")

    # GitHub search
    github_search_match = re.match(
        r"^(?:search github for|find on github)\s+(.+)$",
        command,
    )

    if github_search_match:
        query = github_search_match.group(1).strip()
        url = "https://github.com/search?q=" + quote(query, safe="")
        return open_edge_website("github", url)

    # GitHub profile, website, or repository
    github_match = re.match(
        r"^(?:open|go to|visit)\s+github(?:\s+(.+))?$",
        command,
    )

    if github_match:
        target = (github_match.group(1) or "").strip()

        if not target or target in ["my profile", "my github profile"]:
            url = "https://github.com/Barathvikash08"
        elif target.startswith(("http://", "https://")):
            url = target
        elif target.startswith("github.com/"):
            url = "https://" + target
        else:
            target = target.removeprefix("@")
            url = "https://github.com/" + quote(target, safe="/")

        return open_edge_website("github", url)
    # YouTube search: handle different natural phrases
    youtube_search_match = re.match(
        r"^(?:"
        r"(?:search|find)\s+(.+?)\s+on\s+youtube|"
        r"(?:search|find)\s+youtube\s+for\s+(.+)|"
        r"youtube\s+search\s+for\s+(.+)|"
        r"(?:open\s+)?youtube\s+and\s+search(?:\s+for)?\s+(.+)"
        r")$",
        command,
    )

    if youtube_search_match:
        query = next(
            (group.strip() for group in youtube_search_match.groups() if group),
            "",
        )
        if query:
            url = (
                "https://www.youtube.com/results?search_query="
                + quote(query, safe="")
            )
            return open_edge_website("youtube", url)


    if youtube_search_match:
        query = youtube_search_match.group(1).strip()
        url = (
            "https://www.youtube.com/results?search_query="
            + quote(query, safe="")
        )
        return open_edge_website("youtube", url)


    # Google searches: support several natural phrases
    google_search_match = re.match(
        r"^(?:"
        r"search(?:\s+google)?(?:\s+for)?|"
        r"google\s+search(?:\s+for)?|"
        r"open\s+google\s+and\s+search(?:\s+for)?|"
        r"open\s+google\s+for|"
        r"google\s+for"
        r")\s+(.+)$",
        command,
    )

    if google_search_match:
        query = google_search_match.group(1).strip()
        if query:
            url = "https://www.google.com/search?q=" + quote(query, safe="")
            return open_edge_website("google", url)

    # Open Google homepage only when no search query was given
    if command in ["open google", "go to google", "visit google"]:
        return open_edge_website("google", "https://www.google.com/")
    # YouTube search and play
    youtube_combined_match = re.match(
        r"^(?:open\s+)?youtube\s+and\s+search(?:\s+for)?\s+(.+)$",
        command,
    )

    if youtube_combined_match:
        query = youtube_combined_match.group(1).strip()
        url = (
            "https://www.youtube.com/results?search_query="
            + quote(query, safe="")
        )
        return open_edge_website("youtube", url)

    if command == "open youtube":
        return open_edge_website(
            "youtube", "https://www.youtube.com"
        )

    youtube_search_match = re.match(
        r"^(?:search|find)\s+(.+?)(?:\s+on\s+youtube)?$",
        command,
    )

    if youtube_search_match and command.startswith(("search ", "find ")):
        query = youtube_search_match.group(1).strip()
        url = (
            "https://www.youtube.com/results?search_query="
            + quote(query, safe="")
        )
        return open_edge_website("youtube", url)

    if re.match(r"^(?:play|open youtube and play)\s+.+$", command):
        return play_youtube_video(command)


    # Other websites
    websites = {
        "youtube": "https://www.youtube.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chatgpt.com",
        "spotify": "https://open.spotify.com",
        "instagram": "https://www.instagram.com",
        "facebook": "https://www.facebook.com",
        "linkedin": "https://www.linkedin.com",
        "reddit": "https://www.reddit.com",
        "wikipedia": "https://www.wikipedia.org",
        "amazon": "https://www.amazon.in",
        "whatsapp": "https://web.whatsapp.com",
        "google drive": "https://drive.google.com",
        "google calendar": "https://calendar.google.com",
        "google meet": "https://meet.google.com",
        "google translate": "https://translate.google.com",
    }

    for name, url in websites.items():
        if command == f"open {name}":
            return open_edge_website(name, url)

    # Desktop applications
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "file explorer": "explorer.exe",
        "chrome": "chrome.exe",
    }

    for name, app in apps.items():
        if command == f"open {name}" or command.startswith(f"open {name} "):
            try:
                subprocess.Popen(app)
                opened_stack.append(name)
                print(f"Opening {name}. Added to stack.")
            except OSError as error:
                print(f"Could not open {name}: {error}")
            return True

    return False


def close_application(command):
    if not command.startswith("close "):
        return False

    requested = command[6:].strip().lower()

    aliases = {
        "google maps": "maps",
        "youtube": "youtube",
        "google": "google",
        "gmail": "gmail",
        "google drive": "google drive",
        "chatgpt": "chatgpt",
        "github": "github",
        "spotify": "spotify",
        "instagram": "instagram",
        "whatsapp": "whatsapp",
        "facebook": "facebook",
        "linkedin": "linkedin",
        "reddit": "reddit",
        "wikipedia": "wikipedia",
        "amazon": "amazon",
        "amazon.in": "amazon",
    }

    requested = aliases.get(requested, requested)

    index = None

    for i in range(len(opened_stack) - 1, -1, -1):
        entry = opened_stack[i]
        name = entry["name"] if isinstance(entry, dict) else entry

        if name.lower() == requested:
            index = i
            break

    if index is None:
        print(f"{requested} is not in the stack.")
        return True

    entry = opened_stack[index]

    if isinstance(entry, dict) and entry.get("type") == "website":
        try:
            from playwright.sync_api import sync_playwright

            domains = {
                "youtube": ["youtube.com"],
                "maps": ["google.com/maps", "maps.google.com"],
                "google": ["google.com"],
                "gmail": ["mail.google.com"],
                "github": ["github.com"],
                "chatgpt": ["chatgpt.com", "chat.openai.com"],
                "spotify": ["open.spotify.com"],
                "instagram": ["instagram.com"],
                "whatsapp": ["web.whatsapp.com"],
                "google drive": ["drive.google.com"],
                "facebook": ["facebook.com"],
                "linkedin": ["linkedin.com"],
                "reddit": ["reddit.com"],
                "wikipedia": ["wikipedia.org"],
                "amazon": ["amazon."],
            }

            target_name = entry.get("name", requested).lower()
            patterns = domains.get(target_name, [target_name])

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)

                closed = False

                for context in browser.contexts:
                    for page in reversed(context.pages):
                        page_url = page.url.lower()

                        if any(pattern in page_url for pattern in patterns):
                            page.close()
                            closed = True
                            break

                    if closed:
                        break

            opened_stack.pop(index)

            if closed:
                print(f"Closed the latest {requested} tab.")
            else:
                print(f"Could not find an open tab for {requested}.")

        except Exception as error:
            print(f"Could not close {requested} tab: {error}")

        return True

    print(f"Closing {requested} is not supported for this entry.")
    return True


def start_timer(minutes):
    name = f"Voice Timer {minutes} minutes"
    try:
        save_response = requests.post(
            f"{API_URL}/workflow",
            params={"name": name, "action": "start_timer", "value": minutes},
            timeout=10,
        )
        save_response.raise_for_status()
        run_response = requests.post(f"{API_URL}/workflow/run", params={"name": name}, timeout=10)
        run_response.raise_for_status()
        print("Timer started:", minutes, "minutes")
        print(run_response.json())
    except requests.RequestException as error:
        print("Could not start timer. Is the backend running?")
        print(error)

def control_youtube(action):
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)

            for context in browser.contexts:
                for page in context.pages:
                    if "youtube.com" in page.url.lower():
                        page.bring_to_front()

                        if action == "pause":
                            page.keyboard.press("k")
                        elif action == "next":
                            page.keyboard.press("Shift+n")
                        elif action == "previous":
                            page.keyboard.press("Shift+p")

                        print(f"YouTube action: {action}")
                        return True

            print("No YouTube tab is open.")
            return False

    except Exception as error:
        print(f"YouTube control failed: {error}")
        return False

def main():
    print("Teachable Voice Automation")

    if not start_edge():
        print("Warning: Edge debugging is unavailable.")

    print("Try: Start a timer for five minutes")
    print("Say 'exit' or 'stop listening' to quit")

    try:
        with sr.Microphone() as source:
            print("Adjusting microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            while True:
                print("\nListening...")
                try:
                    audio = recognizer.listen(
                        source,
                        timeout=None,
                        phrase_time_limit=7
)
                    command = recognizer.recognize_google(audio).lower().strip()
                    print("You said:", command)


                    if command in (
                        "start study mode",
                        "study mode",
                        "begin study mode",
                    ):
                            run_study_mode()
                            continue
                    if re.search(r"\b(exit|quit)\b|stop listening", command):
                        print("Voice assistant stopped.")
                        break
                    if close_application(command):
                        continue

                    if switch_tab(command):
                        continue

                    if browser_navigation(command):
                        continue

                    if control_volume(command):
                        continue

                    if open_application(command):
                        continue

                    if "timer" in command:
                        minutes = extract_minutes(command)
                        if minutes is None or minutes <= 0:
                            print("Please say a duration, like ten minutes.")
                            continue
                        start_timer(minutes)

                    else:
                        print("Command not recognized. Try: set a timer for ten minutes.")
                except sr.UnknownValueError:
                    print("Sorry, I couldn't understand. Please try again.")
                except sr.RequestError as error:
                    print("Speech recognition error:", error)
    except KeyboardInterrupt:
        print("\nVoice assistant stopped.")
    except (OSError, AttributeError) as error:
        print("Microphone error:", error)

def switch_tab(command):
    command = command.lower().strip()

    aliases = {
        "youtube": ["youtube.com"],
        "github": ["github.com"],
        "google": ["google.com"],
        "gmail": ["mail.google.com"],
        "chatgpt": ["chatgpt.com", "chat.openai.com"],
    }

    match = re.match(
        r"^(?:switch to|go to|change to)\s+(.+?)\s+tab$",
        command,
    )

    if not match:
        return False

    requested = match.group(1).strip()
    patterns = aliases.get(requested)

    if not patterns:
        print(f"I don't know the website: {requested}")
        return True

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)

            for context in browser.contexts:
                for page in reversed(context.pages):
                    if any(pattern in page.url.lower() for pattern in patterns):
                        page.bring_to_front()
                        print(f"Switched to {requested}.")
                        return True

        print(f"No open tab found for {requested}.")

    except Exception as error:
        print(f"Could not switch tabs: {error}")

    return True


def browser_navigation(command):
    command = command.lower().strip()

    actions = {
        "go back": "back",
        "back": "back",
        "go forward": "forward",
        "forward": "forward",
        "refresh page": "refresh",
        "refresh": "refresh",
        "reload page": "refresh",
        "reload": "refresh",
    }

    action = actions.get(command)

    if action is None:
        return False

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)

            pages = [
                page
                for context in browser.contexts
                for page in context.pages
                if not page.is_closed()
            ]

            if not pages:
                print("No open browser tab found.")
                return True

            page = next(
                (page for page in pages if page.url != "about:blank"),
                pages[-1],
            )

            if action == "back":
                page.go_back()
                print("Went back.")

            elif action == "forward":
                page.go_forward()
                print("Went forward.")

            elif action == "refresh":
                page.reload()
                print("Page refreshed.")

    except Exception as error:
        print(f"Browser navigation failed: {error}")

    return True



def control_volume(command):
    command = command.lower().strip()

    import re

    aliases = {
        "louder": "up",
        "increase sound": "up",
        "sound up": "up",
        "softer": "down",
        "lower sound": "down",
        "sound down": "down",
        "mute": "mute",
        "sound off": "mute",
        "sound on": "unmute",
        "unmute": "unmute",
        "full volume": "full",
        "maximum volume": "full",
    }

    action = aliases.get(command)

    match = re.fullmatch(
        r"(?:(?:set )?volume to )?(\d{1,3})(?: percent|%)?",
        command,
    )

    if action is None and match is None:
        return False

    try:
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume
        current = volume.GetMasterVolumeLevelScalar()

        if action == "up":
            volume.SetMasterVolumeLevelScalar(
                min(1.0, current + 0.10), None
            )
            print("Volume increased.")

        elif action == "down":
            volume.SetMasterVolumeLevelScalar(
                max(0.0, current - 0.10), None
            )
            print("Volume decreased.")

        elif action == "mute":
            volume.SetMute(1, None)
            print("Muted.")

        elif action == "unmute":
            volume.SetMute(0, None)
            print("Sound on.")

        elif action == "full":
            volume.SetMasterVolumeLevelScalar(1.0, None)
            print("Full volume.")

        elif match:
            percentage = int(match.group(1))

            if not 0 <= percentage <= 100:
                print("Choose a number from 0 to 100.")
                return True

            volume.SetMasterVolumeLevelScalar(
                percentage / 100.0, None
            )
            print(f"Volume set to {percentage} percent.")

    except Exception as error:
        print(f"Could not control volume: {error}")

    return True


def run_study_mode():
    try:
        response = requests.post(
            f"{API_URL}/workflow/run",
            params={"name": "Study Mode"},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("action") != "study_mode":
            print("Study Mode workflow did not start:", result)
            return

        print("Study Mode timer started.")

        open_edge_website(
            "youtube",
            "https://www.youtube.com/results?search_query=Java%20tutorials",
        )

        control_volume("30 percent")

        print("Study Mode is ready!")

    except requests.RequestException as error:
        print("Could not start Study Mode. Check that FastAPI is running.")
        print(error)



if __name__ == "__main__":
    main()