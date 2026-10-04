from fastmcp import FastMCP
import subprocess
import os
import pygetwindow as gw
import urllib.parse
import requests
import websocket
import json
import time

mcp = FastMCP(name="Opener")

@mcp.tool
def open_whatsapp() -> str:
    """Open WhatsApp on windows"""
    # subprocess.Popen("start whatsapp:", shell=True)
    subprocess.run(["powershell", "-Command", "start whatsapp:"])
    return "WhatsApp opened"

@mcp.tool
def close_whatsapp() -> str:
    """Forcefully close all WhatsApp instances and background notification processes"""
    
    # List of executable names WhatsApp uses across different versions
    processes_to_kill = ["WhatsApp.exe", "WhatsApp.Root.exe", "WhatsAppDesktop.exe"]
    
    for app in processes_to_kill:
        # /F forces closure, /IM specifies image name, /T kills the process tree (child processes)
        subprocess.run(
            ["taskkill", "/F", "/T", "/IM", app], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
    return "WhatsApp UI and background notifications successfully terminated."

@mcp.tool
def minimize_active_window()->str:
    """Minimize the active window"""
    try:
        active_window = gw.getActiveWindow()

        if active_window:
            window_title = active_window.title
            active_window.minimize()
            return f"{window_title} is minimized."
        else:
            return "no active window found!"
    except Exception as e:
        return "Failed to minimize!"

@mcp.tool
def minimize_all()->str:
    """
    minimize all windows
    """
    windows = gw.getAllWindows()
    for window in windows:
        if window.title:
            try:
                window.minimize()
            except Exception as e:
                continue

    return "All are minimized!"

@mcp.tool
def restore_all()->str:
    """
    restore all windows
    """
    windows = gw.getAllWindows()
    for window in windows:
        if window.title:
            try:
                window.restore()
            except Exception as e:
                continue

    return "All are restored!"

@mcp.tool
def minimize_specific_window(title_keyword: str) -> str:
    """
    Minimize a specific window based on a case-sensitive partial title match.
    
    Args:
        title_keyword (str): The text or application name to look for (e.g., 'Chrome').
    """
    matching_windows = gw.getWindowsWithTitle(title_keyword)
    
    if not matching_windows:
        return f"No window found matching '{title_keyword}'."
        
    target_window = matching_windows[0]
    try:
        target_window.minimize()
        return f"Successfully minimized: '{target_window.title}'"
    except Exception as e:
        return f"Failed to minimize window: {str(e)}"


@mcp.tool
def restore_specific_window(title_keyword: str) -> str:
    """
    Restore a specific window from being minimized based on a case-sensitive partial title match.
    
    Args:
        title_keyword (str): The text or application name to look for (e.g., 'Chrome').
    """
    matching_windows = gw.getWindowsWithTitle(title_keyword)
    
    if not matching_windows:
        return f"No window found matching '{title_keyword}'."
        
    target_window = matching_windows[0]
    try:
        target_window.restore()
        return f"Successfully restored: '{target_window.title}'"
    except Exception as e:
        return f"Failed to restore window: {str(e)}"
            
@mcp.tool
def active_specific(title_keyword: str) -> str:
    """
    Bring a specific window to the foreground and make it active based on a partial title match.
    
    Args:
        title_keyword (str): The text or application name to look for (e.g., 'Chrome').
    """
    matching_windows = gw.getWindowsWithTitle(title_keyword)
    
    if not matching_windows:
        return f"No window found matching '{title_keyword}'."
        
    # Grab the first window object from the list using [0]
    target_window = matching_windows[0]
    
    try:
        # If the window is minimized, restore it first so it can take focus
        if target_window.isMinimized:
            target_window.restore()
            
        target_window.activate()
        return f"Successfully activated: '{target_window.title}'"
    except Exception as e:
        return f"Failed to activate window: {str(e)}"


# @mcp.tool
# def open_youtube(search_query: str = "") -> str:
#     """
#     Open YouTube or reuse an existing YouTube tab.

#     If YouTube is already open in Chrome, navigate that tab.
#     Otherwise, open YouTube in Chrome.
#     """

#     if search_query:
#         encoded_query = urllib.parse.quote_plus(search_query)
#         target_url = (
#             f"https://www.youtube.com/results?search_query={encoded_query}"
#         )
#     else:
#         target_url = "https://www.youtube.com"

#     # Check whether Chrome remote debugging is available
#     try:
#         tabs = requests.get(
#             "http://localhost:9222/json",
#             timeout=1
#         ).json()

#         # Find an existing YouTube tab
#         youtube_tab = next(
#             (
#                 tab for tab in tabs
#                 if "youtube.com" in tab.get("url", "").lower()
#             ),
#             None
#         )

#         if youtube_tab:
#             ws = websocket.create_connection(
#                 youtube_tab["webSocketDebuggerUrl"],
#                 timeout=3
#             )

#             ws.send(json.dumps({
#                 "id": 1,
#                 "method": "Page.navigate",
#                 "params": {
#                     "url": target_url
#                 }
#             }))

#             ws.close()

#             if search_query:
#                 return f"Existing YouTube tab searched for: '{search_query}'"
#             else:
#                 return "Existing YouTube tab opened."

#     except Exception:
#         pass

#     # No existing YouTube tab found.
#     try:
#         chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

#         subprocess.Popen([
#             chrome,
#             target_url
#         ])

#         if search_query:
#             return f"YouTube opened and searched for: '{search_query}'"
#         else:
#             return "YouTube opened."

#     except FileNotFoundError:
#         os.startfile(target_url)

#         if search_query:
#             return f"YouTube opened and searched for: '{search_query}'"
#         else:
#             return "YouTube opened."

#     except Exception as e:
#         return f"Error opening YouTube: {e}"

@mcp.tool
def open_youtube(search_query: str = "") -> str:
    """
    Open YouTube or reuse an existing YouTube tab.

    If YouTube is already open in the CDP-controlled Chrome,
    navigate that tab. Otherwise, create a new tab in the
    same Chrome instance.
    """

    if search_query:
        encoded_query = urllib.parse.quote_plus(search_query)
        target_url = (
            f"https://www.youtube.com/results?search_query={encoded_query}"
        )
    else:
        target_url = "https://www.youtube.com/"

    try:
        # Get tabs from the CDP-controlled Chrome
        response = requests.get(
            "http://127.0.0.1:9222/json",
            timeout=3
        )

        response.raise_for_status()

        tabs = response.json()

        # --------------------------------------------------
        # Find existing YouTube tab
        # --------------------------------------------------

        youtube_tab = next(
            (
                tab
                for tab in tabs
                if tab.get("type") == "page"
                and "youtube.com" in tab.get("url", "").lower()
            ),
            None
        )

        if youtube_tab:

            ws_url = youtube_tab.get("webSocketDebuggerUrl")

            if not ws_url:
                return "YouTube tab found, but WebSocket URL is unavailable."

            ws = websocket.create_connection(
                ws_url,
                timeout=5
            )

            ws.send(json.dumps({
                "id": 1,
                "method": "Page.navigate",
                "params": {
                    "url": target_url
                }
            }))

            # Wait for Chrome's response
            while True:
                message = json.loads(ws.recv())

                if message.get("id") == 1:
                    break

            ws.close()

            if search_query:
                return (
                    f"Existing YouTube tab navigated to search: "
                    f"'{search_query}'"
                )

            return "Existing YouTube tab navigated to YouTube."

        # --------------------------------------------------
        # No YouTube tab → create one through CDP
        # --------------------------------------------------

        response = requests.put(
            "http://127.0.0.1:9222/json/new",
            timeout=5
        )

        response.raise_for_status()

        new_tab = response.json()

        ws_url = new_tab.get("webSocketDebuggerUrl")

        if not ws_url:
            return "New tab created, but WebSocket URL is unavailable."

        ws = websocket.create_connection(
            ws_url,
            timeout=5
        )

        ws.send(json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {
                "url": target_url
            }
        }))

        while True:
            message = json.loads(ws.recv())

            if message.get("id") == 1:
                break

        ws.close()

        if search_query:
            return (
                f"New YouTube tab opened and searched for: "
                f"'{search_query}'"
            )

        return "New YouTube tab opened."

    except requests.ConnectionError:
        return (
            "Chrome CDP is not running on port 9222."
        )

    except websocket.WebSocketException as e:
        return f"Chrome WebSocket error: {e}"

    except Exception as e:
        return f"Error opening YouTube: {e}"


CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP = "http://127.0.0.1:9222"

MCP_PROFILE = os.path.join(
    os.environ["TEMP"],
    "chrome-mcp"
)


def cdp_available():
    try:
        response = requests.get(
            f"{CDP}/json/version",
            timeout=1
        )
        return response.status_code == 200

    except requests.RequestException:
        return False





@mcp.tool
def start_chrome() -> str:
    """
    Start an MCP-controlled Chrome instance with CDP enabled.
    """

    if cdp_available():
        return "Chrome CDP is already running."

    try:
        subprocess.Popen([
            CHROME,
            "--remote-debugging-port=9222",
            "--remote-allow-origins=http://127.0.0.1:9222",
            f"--user-data-dir={MCP_PROFILE}"
        ])

    except Exception as e:
        return f"Failed to start Chrome: {e}"

    for _ in range(20):
        if cdp_available():
            return "Chrome started successfully with CDP on port 9222."

        time.sleep(0.5)

    return "Chrome started, but CDP did not become available."



@mcp.tool
def google_search(keyword: str) -> str:
    """Search Google using the MCP-controlled Chrome."""

    if not cdp_available():
        return "Chrome CDP is not running. Call start_chrome first."

    query = urllib.parse.quote_plus(keyword)
    url = f"https://www.google.com/search?q={query}"

    try:
        response = requests.put(
            f"{CDP}/json/new?{url}",
            timeout=5
        )

        if response.status_code in (200, 201):
            return f"Opened Google search for '{keyword}'."

        return f"Chrome error: {response.status_code} {response.text}"

    except Exception as e:
        return f"Error: {e}"

@mcp.tool
def open_vscode() -> str:
    """Open Visual Studio Code."""

    vscode = os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
    )

    try:
        subprocess.Popen([vscode])
        return "VS Code opened."

    except FileNotFoundError:
        return f"VS Code not found at: {vscode}"

    except Exception as e:
        return f"Error opening VS Code: {e}"

@mcp.tool
def close_vs_code() -> str:
    """Forcefully close all Visual Studio Code instances and processes."""

    try:
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/IM", "Code.exe"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return "VS Code closed successfully."

        # taskkill returns an error when Code.exe isn't running
        if "not found" in result.stderr.lower():
            return "VS Code is not running."

        return f"Failed to close VS Code: {result.stderr.strip()}"

    except Exception as e:
        return f"Error closing VS Code: {e}"

import pyautogui

@mcp.tool
def open_from_start(app: str) -> str:
    """Open a Windows application using the Start menu."""

    try:
        pyautogui.press("win")
        time.sleep(0.5)

        pyautogui.write(app, interval=0.03)
        time.sleep(0.5)

        pyautogui.press("enter")

        return f"Opened {app} from Windows Start."

    except Exception as e:
        return f"Error: {e}"

@mcp.tool
def list_chrome_tabs() -> str:
    """
    List all open Chrome tabs with their titles and URLs.
    """

    try:
        response = requests.get(
            f"{CDP}/json",
            timeout=3
        )

        if response.status_code != 200:
            return "Unable to get Chrome tabs."

        tabs = response.json()

        pages = [
            tab for tab in tabs
            if tab.get("type") == "page"
        ]

        if not pages:
            return "No Chrome tabs found."

        result = []

        for index, tab in enumerate(pages, start=1):
            result.append(
                f"{index}. {tab.get('title', 'Untitled')}\n"
                f"   URL: {tab.get('url', '')}\n"
                f"   ID: {tab.get('id', '')}"
            )

        return "\n\n".join(result)

    except requests.ConnectionError:
        return "Chrome CDP is not running on port 9222."

    except Exception as e:
        return f"Error listing tabs: {e}"


@mcp.tool
def new_chrome_tab(url: str = "about:blank") -> str:
    """
    Open a new Chrome tab.

    Args:
        url: URL to open in the new tab.
    """

    try:
        response = requests.put(
            f"{CDP}/json/new?{url}",
            timeout=5
        )

        if response.status_code not in (200, 201):
            return (
                f"Failed to create tab: "
                f"{response.status_code} {response.text}"
            )

        tab = response.json()

        return (
            f"New Chrome tab created.\n"
            f"Title: {tab.get('title', '')}\n"
            f"URL: {tab.get('url', '')}\n"
            f"ID: {tab.get('id', '')}"
        )

    except requests.ConnectionError:
        return "Chrome CDP is not running."

    except Exception as e:
        return f"Error creating tab: {e}"


@mcp.tool
def close_chrome_tab(title: str) -> str:
    """
    Close a Chrome tab using its title.

    Args:
        title: Full or partial title of the tab.
    """

    try:
        response = requests.get(
            f"{CDP}/json",
            timeout=3
        )

        if response.status_code != 200:
            return "Unable to retrieve Chrome tabs."

        tabs = response.json()

        pages = [
            tab for tab in tabs
            if tab.get("type") == "page"
        ]

        # Exact match first
        target = next(
            (
                tab for tab in pages
                if tab.get("title", "").lower() == title.lower()
            ),
            None
        )

        # Partial match
        if target is None:
            target = next(
                (
                    tab for tab in pages
                    if title.lower() in tab.get("title", "").lower()
                ),
                None
            )

        if target is None:
            return f"No tab found with title: {title}"

        tab_id = target.get("id")

        close_response = requests.get(
            f"{CDP}/json/close/{tab_id}",
            timeout=3
        )

        if close_response.status_code == 200:
            return f"Closed tab: {target.get('title')}"

        return (
            f"Failed to close tab: "
            f"{close_response.status_code} "
            f"{close_response.text}"
        )

    except requests.ConnectionError:
        return "Chrome CDP is not running."

    except Exception as e:
        return f"Error closing tab: {e}"


@mcp.tool
def focus_chrome_tab(title: str) -> str:
    """
    Bring a Chrome tab to the foreground using its title.

    Args:
        title: Full or partial title of the tab.
    """

    try:
        response = requests.get(
            f"{CDP}/json",
            timeout=3
        )

        if response.status_code != 200:
            return "Unable to retrieve Chrome tabs."

        tabs = response.json()

        pages = [
            tab for tab in tabs
            if tab.get("type") == "page"
        ]

        target = next(
            (
                tab for tab in pages
                if tab.get("title", "").lower() == title.lower()
            ),
            None
        )

        if target is None:
            target = next(
                (
                    tab for tab in pages
                    if title.lower() in tab.get("title", "").lower()
                ),
                None
            )

        if target is None:
            return f"No tab found with title: {title}"

        tab_id = target.get("id")

        activate_response = requests.get(
            f"{CDP}/json/activate/{tab_id}",
            timeout=3
        )

        if activate_response.status_code == 200:
            return f"Focused tab: {target.get('title')}"

        return (
            f"Failed to focus tab: "
            f"{activate_response.text}"
        )

    except requests.ConnectionError:
        return "Chrome CDP is not running."

    except Exception as e:
        return f"Error focusing tab: {e}"


import json
import requests
import websocket

CDP = "http://127.0.0.1:9222"


def get_tab_by_title(title: str):
    response = requests.get(f"{CDP}/json", timeout=3)
    response.raise_for_status()

    tabs = [
        tab for tab in response.json()
        if tab.get("type") == "page"
    ]

    # Exact match
    for tab in tabs:
        if tab.get("title", "").lower() == title.lower():
            return tab

    # Partial match
    for tab in tabs:
        if title.lower() in tab.get("title", "").lower():
            return tab

    return None

def execute_js(tab, javascript):
    ws_url = tab.get("webSocketDebuggerUrl")

    if not ws_url:
        raise Exception("Tab does not have a WebSocket debugger URL.")

    ws = websocket.create_connection(
        ws_url,
        timeout=5
    )

    command = {
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": javascript,
            "returnByValue": True,
            "awaitPromise": True
        }
    }

    ws.send(json.dumps(command))

    while True:
        message = json.loads(ws.recv())

        if message.get("id") == 1:
            break

    ws.close()

    if "exceptionDetails" in message.get("result", {}):
        raise Exception(
            str(message["result"]["exceptionDetails"])
        )

    return (
        message
        .get("result", {})
        .get("result", {})
        .get("value")
    )

# @mcp.tool
# def read_chrome_dom(title: str, selector: str = "") -> str:
#     """
#     Read the DOM of an open Chrome tab.

#     Args:
#         title:
#             Full or partial title of the Chrome tab.

#         selector:
#             Optional CSS selector.
#             If provided, only matching elements are returned.
#             Example: "body", "h1", ".article", "#content"
#     """

#     try:
#         tab = get_tab_by_title(title)

#         if not tab:
#             return f"No Chrome tab found matching '{title}'."

#         ws_url = tab.get("webSocketDebuggerUrl")

#         if not ws_url:
#             return "Chrome did not provide a WebSocket debugger URL."

#         ws = websocket.create_connection(
#             ws_url,
#             timeout=5
#         )

#         # JavaScript to execute inside the page
#         if selector:
#             javascript = """
#             (selector) => {
#                 const elements = document.querySelectorAll(selector);

#                 return Array.from(elements).map((el, index) => ({
#                     index: index,
#                     tag: el.tagName,
#                     text: el.innerText,
#                     html: el.outerHTML
#                 }));
#             }
#             """
#         else:
#             javascript = """
#             () => ({
#                 title: document.title,
#                 url: location.href,
#                 text: document.body ? document.body.innerText : "",
#                 html: document.documentElement.outerHTML
#             })
#             """

#         # Send Runtime.evaluate
#         command = {
#             "id": 1,
#             "method": "Runtime.evaluate",
#             "params": {
#                 "expression": f"({javascript})(arguments[0])"
#                 if selector
#                 else f"({javascript})()",

#                 "returnByValue": True,

#                 "awaitPromise": True
#             }
#         }

#         if selector:
#             command["params"]["arguments"] = [
#                 {"value": selector}
#             ]

#         ws.send(json.dumps(command))

#         # Wait for response
#         while True:
#             message = json.loads(ws.recv())

#             if message.get("id") == 1:
#                 break

#         ws.close()

#         result = message.get("result", {})

#         exception = result.get("exceptionDetails")

#         if exception:
#             return f"JavaScript error: {exception}"

#         value = (
#             result
#             .get("result", {})
#             .get("value")
#         )

#         if value is None:
#             return "No DOM content returned."

#         # Limit output so an enormous page doesn't overwhelm the MCP context
#         output = json.dumps(
#             value,
#             indent=2,
#             ensure_ascii=False
#         )

#         MAX_LENGTH = 30000

#         if len(output) > MAX_LENGTH:
#             output = (
#                 output[:MAX_LENGTH]
#                 + "\n\n...[DOM truncated]..."
#             )

#         return output

#     except requests.RequestException:
#         return "Chrome CDP is not available on port 9222."

#     except websocket.WebSocketException as e:
#         return f"Chrome WebSocket error: {e}"

#     except Exception as e:
#         return f"Error reading DOM: {e}"


@mcp.tool
def read_page(title: str) -> str:
    """
    Read a Chrome page in an AI-friendly format.

    Returns:
        - Page title
        - URL
        - Headings
        - Links
        - Buttons
        - Form inputs
        - Visible page text

    Args:
        title:
            Full or partial title of the Chrome tab.
    """

    try:
        tab = get_tab_by_title(title)

        if not tab:
            return f"No Chrome tab found matching '{title}'."

        javascript = r"""
        (() => {

            function clean(text) {
                return (text || "")
                    .replace(/\s+/g, " ")
                    .trim();
            }

            function visible(element) {
                const style = window.getComputedStyle(element);

                const rect = element.getBoundingClientRect();

                return (
                    style.display !== "none" &&
                    style.visibility !== "hidden" &&
                    style.opacity !== "0" &&
                    rect.width > 0 &&
                    rect.height > 0
                );
            }

            const headings = Array.from(
                document.querySelectorAll("h1,h2,h3,h4,h5,h6")
            )
            .filter(visible)
            .map(el => ({
                tag: el.tagName,
                text: clean(el.innerText)
            }))
            .filter(x => x.text);

            const links = Array.from(
                document.querySelectorAll("a")
            )
            .filter(visible)
            .map((el, index) => ({
                index,
                text: clean(el.innerText),
                href: el.href
            }))
            .filter(x => x.text || x.href);

            const buttons = Array.from(
                document.querySelectorAll(
                    "button, input[type='button'], input[type='submit']"
                )
            )
            .filter(visible)
            .map((el, index) => ({
                index,
                text: clean(
                    el.innerText ||
                    el.value ||
                    el.getAttribute("aria-label")
                )
            }))
            .filter(x => x.text);

            const inputs = Array.from(
                document.querySelectorAll(
                    "input, textarea, select"
                )
            )
            .filter(visible)
            .map((el, index) => ({
                index,
                tag: el.tagName,
                type: el.type || "",
                name: el.name || "",
                placeholder: el.placeholder || "",
                value: el.value || "",
                ariaLabel: el.getAttribute("aria-label") || ""
            }));

            const bodyText = document.body
                ? document.body.innerText
                : "";

            return {
                title: document.title,
                url: window.location.href,
                headings,
                links,
                buttons,
                inputs,
                text: clean(bodyText)
            };

        })()
        """

        result = execute_js(tab, javascript)

        if not result:
            return "No page information returned."

        output = []

        output.append(
            f"PAGE: {result['title']}"
        )

        output.append(
            f"URL: {result['url']}"
        )

        # -----------------------------
        # HEADINGS
        # -----------------------------

        if result["headings"]:

            output.append("\nHEADINGS:")

            for heading in result["headings"]:
                output.append(
                    f"- [{heading['tag']}] {heading['text']}"
                )

        # -----------------------------
        # LINKS
        # -----------------------------

        if result["links"]:

            output.append("\nLINKS:")

            for link in result["links"][:100]:

                text = link["text"] or "(no text)"

                output.append(
                    f"- [{link['index']}] "
                    f"{text} → {link['href']}"
                )

        # -----------------------------
        # BUTTONS
        # -----------------------------

        if result["buttons"]:

            output.append("\nBUTTONS:")

            for button in result["buttons"]:

                output.append(
                    f"- [{button['index']}] "
                    f"{button['text']}"
                )

        # -----------------------------
        # INPUTS
        # -----------------------------

        if result["inputs"]:

            output.append("\nINPUTS:")

            for field in result["inputs"]:

                output.append(
                    f"- [{field['index']}] "
                    f"{field['tag']} "
                    f"type={field['type']} "
                    f"name={field['name']} "
                    f"placeholder={field['placeholder']} "
                    f"aria-label={field['ariaLabel']}"
                )

        # -----------------------------
        # TEXT
        # -----------------------------

        if result["text"]:

            text = result["text"]

            # Avoid gigantic responses
            if len(text) > 20000:
                text = text[:20000] + "\n...[text truncated]..."

            output.append("\nPAGE TEXT:")
            output.append(text)

        return "\n".join(output)

    except requests.RequestException:
        return "Chrome CDP is unavailable on port 9222."

    except websocket.WebSocketException as e:
        return f"Chrome WebSocket error: {e}"

    except Exception as e:
        return f"Error reading page: {e}"


@mcp.tool
def kill_application(process_name: str) -> str:
    """
    Forcefully terminate an application by its process name.

    Args:
        process_name: Executable name, e.g. "notepad.exe", "Code.exe".
    """

    if not process_name.lower().endswith(".exe"):
        process_name += ".exe"

    try:
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/IM", process_name],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return f"{process_name} terminated successfully."

        return f"Could not terminate {process_name}: {result.stderr.strip()}"

    except Exception as e:
        return f"Error terminating {process_name}: {e}"
    
# if __name__ == "__main__":
#     mcp.run(transport="http", host="0.0.0.0", port=9000)