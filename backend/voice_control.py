import os
import re
import subprocess
import time
from urllib.parse import quote, urlparse

import requests
import speech_recognition as sr


EDGE_DEBUG_URL = "http://127.0.0.1:9222"
API_URL = "http://127.0.0.1:8000"

opened_stack = []
recognizer = sr.Recognizer()

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

WEBSITES = {
    "youtube": "https://www.youtube.com/",
    "google": "https://www.google.com/",
    "google maps": "https://maps.google.com/",
    "maps": "https://maps.google.com/",
    "gmail": "https://mail.google.com/",
    "github": "https://github.com/",
    "chatgpt": "https://chatgpt.com/",
    "spotify": "https://open.spotify.com/",
    "instagram": "https://www.instagram.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "google drive": "https://drive.google.com/",
    "google calendar": "https://calendar.google.com/",
    "google meet": "https://meet.google.com/",
    "google translate": "https://translate.google.com/",
    "facebook": "https://www.facebook.com/",
    "linkedin": "https://www.linkedin.com/",
    "reddit": "https://www.reddit.com/",
    "wikipedia": "https://www.wikipedia.org/",
    "amazon": "https://www.amazon.in/",
    "leetcode": "https://leetcode.com/",
}


def start_edge():
    import requests

    debug_url = f"{EDGE_DEBUG_URL}/json/version"

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

    edge_exe = next(
        (path for path in edge_paths if os.path.exists(path)),
        None,
    )

    if not edge_exe:
        print("Could not find Microsoft Edge.")
        return False

    profile = os.path.join(
        os.environ.get("TEMP", "."),
        "VoiceAssistantEdge",
    )

    try:
        subprocess.Popen([
            edge_exe,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile}",
        ])
    except OSError as error:
        print(f"Could not start Edge: {error}")
        return False

    for _ in range(15):
        time.sleep(1)
        try:
            response = requests.get(debug_url, timeout=2)
            if response.ok:
                print("Edge started and is ready.")
                return True
        except requests.RequestException:
            pass

    print("Edge debugging did not become available.")
    return False


def extract_minutes(command):
    number_pattern = r"\d+|" + "|".join(NUMBER_WORDS.keys())

    match = re.search(
        rf"\b({number_pattern})\s*(?:minutes?|mins?|min)\b",
        command.lower(),
    )

    if not match:
        return None

    value = match.group(1)

    return int(value) if value.isdigit() else NUMBER_WORDS[value]


def open_edge_website(name, url, new_tab=False):
    try:
        from playwright.sync_api import sync_playwright

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
                target_host = urlparse(url).netloc.lower()
                page = None

                for existing_page in pages:
                    current_host = urlparse(
                        existing_page.url
                    ).netloc.lower()

                    if current_host == target_host:
                        page = existing_page
                        break

                if page is None:
                    page = pages[0] if pages else context.new_page()

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.bring_to_front()

            opened_stack[:] = [
                entry
                for entry in opened_stack
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

            print(f"Opened {name}.")
            return True

    except Exception as error:
        print(f"Could not open {name} in Edge: {error}")
        return False


def play_youtube_video(command):
    try:
        from playwright.sync_api import sync_playwright

        text = re.sub(
            r"^(?:play|open|search|find)\s+(?:for\s+)?",
            "",
            command.strip(),
            flags=re.I,
        )

        text = re.sub(
            r"\s+(?:on|in)\s+youtube$",
            "",
            text,
            flags=re.I,
        ).strip()

        if not text:
            print("Please specify a video to play.")
            return False

        search_url = (
            "https://www.youtube.com/results?search_query="
            + quote(text, safe="")
        )

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)
            context = browser.contexts[0]

            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            page.locator("ytd-video-renderer").first.wait_for(
                timeout=20000
            )

            videos = page.locator("ytd-video-renderer")

            for i in range(min(videos.count(), 30)):
                link = videos.nth(i).locator("a#video-title").first
                href = link.get_attribute("href") or ""

                if "/watch" not in href:
                    continue

                video_url = (
                    href
                    if href.startswith("http")
                    else "https://www.youtube.com" + href
                )

                page.goto(
                    video_url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                page.bring_to_front()
                opened_stack.append({
                    "type": "website",
                    "name": "youtube",
                })

                print("Opened YouTube video.")
                return True

            print("No YouTube video was found.")
            return False

    except Exception as error:
        print(f"Could not play YouTube video: {error}")
        return False


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


def open_application(command):
    command = command.lower().strip()

    if command in (
        "open a new tab",
        "new tab",
        "create a new tab",
    ):
        return open_edge_website(
            "new tab",
            "about:blank",
            new_tab=True,
        )

    new_tab_match = re.match(
        r"^(?:open|create)\s+(?:a\s+)?new tab"
        r"(?:\s+with|\s+for)?\s+(.+)$",
        command,
    )

    if new_tab_match:
        target = new_tab_match.group(1).strip()

        if target in WEBSITES:
            return open_edge_website(
                target,
                WEBSITES[target],
                new_tab=True,
            )

        return False

    if command in ("pause youtube", "pause video"):
        return control_youtube("pause")

    if command in ("next youtube video", "next video"):
        return control_youtube("next")

    if command in (
        "previous youtube video",
        "previous video",
        "prev video",
    ):
        return control_youtube("previous")

    directions_match = re.match(
        r"^(?:give me directions to|directions to|navigate to|"
        r"take me to|go to)\s+(.+)$",
        command,
    )

    maps_search_match = re.match(
        r"^(?:search|find|show)\s+(.+?)\s+"
        r"(?:on|in)\s+(?:google\s+)?maps$",
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

    if command in ("open maps", "open google maps", "launch maps"):
        return open_edge_website(
            "maps",
            WEBSITES["google maps"],
        )

    github_search = re.match(
        r"^(?:search github for|find on github)\s+(.+)$",
        command,
    )

    if github_search:
        url = (
            "https://github.com/search?q="
            + quote(github_search.group(1).strip(), safe="")
        )
        return open_edge_website("github", url)

    github_match = re.match(
        r"^(?:open|go to|visit)\s+github(?:\s+(.+))?$",
        command,
    )

    if github_match:
        target = (github_match.group(1) or "").strip()

        if not target or target in (
            "my profile",
            "my github profile",
        ):
            url = "https://github.com/Barathvikash08"
        elif target.startswith(("http://", "https://")):
            url = target
        elif target.startswith("github.com/"):
            url = "https://" + target
        else:
            url = (
                "https://github.com/"
                + quote(target.removeprefix("@"), safe="/")
            )

        return open_edge_website("github", url)

    youtube_search = re.match(
        r"^(?:"
        r"(?:search|find)\s+(.+?)\s+on\s+youtube|"
        r"(?:search|find)\s+youtube\s+for\s+(.+)|"
        r"youtube\s+search\s+for\s+(.+)|"
        r"(?:open\s+)?youtube\s+and\s+search(?:\s+for)?\s+(.+)"
        r")$",
        command,
    )

    if youtube_search:
        query = next(
            (
                group.strip()
                for group in youtube_search.groups()
                if group
            ),
            "",
        )

        if query:
            url = (
                "https://www.youtube.com/results?search_query="
                + quote(query, safe="")
            )
            return open_edge_website("youtube", url)

    google_search = re.match(
        r"^(?:"
        r"search(?:\s+google)?(?:\s+for)?|"
        r"google\s+search(?:\s+for)?|"
        r"open\s+google\s+and\s+search(?:\s+for)?|"
        r"open\s+google\s+for|"
        r"google\s+for"
        r")\s+(.+)$",
        command,
    )

    if google_search:
        query = google_search.group(1).strip()
        url = (
            "https://www.google.com/search?q="
            + quote(query, safe="")
        )
        return open_edge_website("google", url)

    if command in ("open google", "go to google", "visit google"):
        return open_edge_website("google", WEBSITES["google"])

    youtube_combined = re.match(
        r"^(?:open\s+)?youtube\s+and\s+search(?:\s+for)?\s+(.+)$",
        command,
    )

    if youtube_combined:
        url = (
            "https://www.youtube.com/results?search_query="
            + quote(youtube_combined.group(1).strip(), safe="")
        )
        return open_edge_website("youtube", url)

    if command == "open youtube":
        return open_edge_website("youtube", WEBSITES["youtube"])

    if command.startswith(("play ", "open youtube and play ")):
        return play_youtube_video(command)

    # LeetCode and other websites.
    # This explicitly fixes the previous Code Mode failure.
    for name, url in WEBSITES.items():
        if command in (
            f"open {name}",
            f"go to {name}",
            f"visit {name}",
            name,
        ):
            return open_edge_website(name, url)

    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "file explorer": "explorer.exe",
        "chrome": "chrome.exe",
    }

    for name, executable in apps.items():
        if command == f"open {name}" or command.startswith(
            f"open {name} "
        ):
            try:
                subprocess.Popen(executable)
                opened_stack.append(name)
                print(f"Opening {name}.")
                return True
            except OSError as error:
                print(f"Could not open {name}: {error}")
                return False

    return False


def close_application(command):
    command = command.strip().lower()

    if not command.startswith("close "):
        return False

    requested = command[6:].strip()

    aliases = {
        "google maps": "maps",
        "leetcode": "leetcode",
        "google drive": "google drive",
        "amazon.in": "amazon",
    }

    requested = aliases.get(requested, requested)

    domains = {
        "youtube": ["youtube.com"],
        "maps": ["google.com/maps", "maps.google.com"],
        "google": ["google.com"],
        "gmail": ["mail.google.com"],
        "github": ["github.com"],
        "leetcode": ["leetcode.com"],
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

    patterns = domains.get(requested)

    if not patterns:
        print(f"Closing {requested} is not supported.")
        return True

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(EDGE_DEBUG_URL)

            for context in browser.contexts:
                for page in reversed(context.pages):
                    if any(
                        pattern in page.url.lower()
                        for pattern in patterns
                    ):
                        page.close()
                        print(f"Closed {requested}.")
                        return True

        print(f"No open tab found for {requested}.")
        return True

    except Exception as error:
        print(f"Could not close {requested}: {error}")
        return True


def start_timer(minutes):
    name = f"Voice Timer {minutes} minutes"

    try:
        save_response = requests.post(
            f"{API_URL}/workflow",
            params={
                "name": name,
                "action": "start_timer",
                "value": minutes,
            },
            timeout=10,
        )
        save_response.raise_for_status()

        run_response = requests.post(
            f"{API_URL}/workflow/run",
            params={"name": name},
            timeout=10,
        )
        run_response.raise_for_status()

        print("Timer started:", minutes, "minutes")
        print(run_response.json())

    except requests.RequestException as error:
        print("Could not start timer. Is the backend running?")
        print(error)


def switch_tab(command):
    command = command.lower().strip()

    aliases = {
        "youtube": ["youtube.com"],
        "github": ["github.com"],
        "google": ["google.com"],
        "gmail": ["mail.google.com"],
        "chatgpt": ["chatgpt.com", "chat.openai.com"],
        "leetcode": ["leetcode.com"],
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
                    if any(
                        pattern in page.url.lower()
                        for pattern in patterns
                    ):
                        page.bring_to_front()
                        print(f"Switched to {requested}.")
                        return True

        print(f"No open tab found for {requested}.")

    except Exception as error:
        print(f"Could not switch tabs: {error}")

    return True


def browser_navigation(command):
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

    action = actions.get(command.lower().strip())

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
                (item for item in pages if item.url != "about:blank"),
                pages[-1],
            )

            if action == "back":
                page.go_back()
                print("Went back.")
            elif action == "forward":
                page.go_forward()
                print("Went forward.")
            else:
                page.reload()
                print("Page refreshed.")

    except Exception as error:
        print(f"Browser navigation failed: {error}")

    return True


def control_volume(command):
    from pycaw.pycaw import AudioUtilities

    command = command.lower().strip()

    aliases = {
        "louder": "up",
        "increase volume": "up",
        "increase the volume": "up",
        "volume up": "up",
        "turn up the volume": "up",
        "make it louder": "up",
        "increase sound": "up",
        "sound up": "up",
        "softer": "down",
        "decrease volume": "down",
        "volume down": "down",
        "turn down the volume": "down",
        "lower sound": "down",
        "sound down": "down",
        "mute": "mute",
        "sound off": "mute",
        "unmute": "unmute",
        "sound on": "unmute",
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
        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume
        current = volume.GetMasterVolumeLevelScalar()

        if action == "up":
            target = min(1.0, current + 0.10)
        elif action == "down":
            target = max(0.0, current - 0.10)
        elif action == "mute":
            volume.SetMute(1, None)
            print("Volume muted.")
            return True
        elif action == "unmute":
            volume.SetMute(0, None)
            print("Volume unmuted.")
            return True
        elif action == "full":
            target = 1.0
        else:
            percentage = int(match.group(1))

            if not 0 <= percentage <= 100:
                print("Choose a volume between 0 and 100.")
                return False

            target = percentage / 100.0

        volume.SetMasterVolumeLevelScalar(target, None)
        actual = volume.GetMasterVolumeLevelScalar()

        if abs(actual - target) > 0.02:
            print("Volume change could not be confirmed.")
            return False

        print(f"Volume changed: {current:.0%} -> {actual:.0%}")
        return True

    except Exception as error:
        print(f"Could not control volume: {error}")
        return False


def run_study_mode():
    try:
        response = requests.post(
            f"{API_URL}/command/execute",
            json={"command": "start study mode"},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        print("Study Mode response:", result)

        if result.get("success") is False:
            print("Study Mode failed:", result.get("message"))

    except requests.RequestException as error:
        print("Could not start Study Mode.")
        print(error)


def run_code_mode():
    try:
        response = requests.post(
            f"{API_URL}/command/execute",
            json={"command": "start code mode"},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        print("Code Mode response:", result)

        if result.get("success") is False:
            print("Code Mode failed:", result.get("message"))

    except requests.RequestException as error:
        print("Could not start Code Mode.")
        print(error)


def main():
    print("Teachable Voice Automation")

    if not start_edge():
        print("Warning: Edge debugging is unavailable.")

    print("Say 'start study mode' or 'start code mode'.")
    print("Say 'start a timer for five minutes' to start a timer.")
    print("Say 'exit' or 'stop listening' to quit.")

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
                        phrase_time_limit=7,
                    )

                    command = recognizer.recognize_google(
                        audio,
                        language="en-IN",
                    ).lower().strip()

                    print("You said:", command)

                    if command in (
                        "start study mode",
                        "study mode",
                        "begin study mode",
                    ):
                        run_study_mode()
                        continue

                    if command in (
                        "start code mode",
                        "code mode",
                        "begin code mode",
                        "start coding mode",
                        "coding mode",
                    ):
                        run_code_mode()
                        continue

                    if re.search(
                        r"\b(exit|quit)\b|stop listening",
                        command,
                    ):
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
                            print(
                                "Please say a duration, "
                                "like ten minutes."
                            )
                            continue

                        start_timer(minutes)
                        continue

                    print(
                        "Command not recognized. Try Study Mode, "
                        "Code Mode, a website, or a timer."
                    )

                except sr.UnknownValueError:
                    print("Sorry, I couldn't understand. Try again.")

                except sr.RequestError as error:
                    print("Speech recognition error:", error)

    except KeyboardInterrupt:
        print("\nVoice assistant stopped.")

    except (OSError, AttributeError) as error:
        print("Microphone error:", error)


if __name__ == "__main__":
    main()