"""Pixiv authentication setup script

Obtains a Pixiv refresh token via the PKCE OAuth flow and saves it to the .env file.
Does not depend on Playwright or Selenium; instead, the user logs in with their own
browser and pastes the callback URL.

Usage:
    uv run python setup_token.py                  # Log in via PKCE flow (recommended)
    uv run python setup_token.py --refresh TOKEN   # Refresh an existing token
    uv run python setup_token.py --token TOKEN     # Save a token directly
"""

import argparse
import base64
import hashlib
import pathlib
import secrets
import sys
import urllib.parse
import webbrowser

import requests

ENV_FILE = pathlib.Path(__file__).parent / ".env"

# Pixiv OAuth constants (shared by pixivpy3 / gppt)
CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
USER_AGENT = "PixivAndroidApp/5.0.234 (Android 14; Pixel 8)"


def _update_env_file(key: str, value: str) -> None:
    """Write a key to the .env file (overwriting it if it already exists)"""
    lines: list[str] = []
    found = False

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pkce_params() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge (S256)"""
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        )
        .rstrip(b"=")
        .decode("ascii")
    )
    return code_verifier, code_challenge


def _build_login_url(code_challenge: str) -> str:
    """Build the Pixiv OAuth login URL"""
    params = {
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    }
    return f"{LOGIN_URL}?{urllib.parse.urlencode(params)}"


def _exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange an authorization code for an access_token / refresh_token"""
    resp = requests.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": REDIRECT_URI,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _refresh_token_request(refresh_token: str) -> dict:
    """Obtain a new token using an existing refresh_token"""
    resp = requests.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": refresh_token,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _open_browser(url: str) -> bool:
    """Open a URL in the browser. Also supports WSL2 environments."""
    import shutil
    import subprocess

    # WSL2: use wslview (from the wslu package) to open the Windows-side browser
    wslview = shutil.which("wslview")
    if wslview:
        try:
            subprocess.run([wslview, url], capture_output=True, timeout=5)
            return True
        except Exception:
            pass

    # WSL2: fall back to explorer.exe
    explorer = shutil.which("explorer.exe")
    if explorer:
        try:
            subprocess.run([explorer, url], capture_output=True, timeout=5)
            return True
        except Exception:
            pass

    # Standard Linux/macOS
    try:
        return webbrowser.open(url)
    except Exception:
        return False


def _extract_code(callback_url: str) -> str | None:
    """Extract the authorization code from a callback URL or direct input"""
    callback_url = callback_url.strip()

    # For URL format: look for ?code=xxx or #code=xxx
    if "code=" in callback_url:
        parsed = urllib.parse.urlparse(callback_url)
        # From query parameters
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            return params["code"][0]
        # From the fragment
        params = urllib.parse.parse_qs(parsed.fragment)
        if "code" in params:
            return params["code"][0]

    # When only the code is pasted (a long string of alphanumerics and symbols)
    if len(callback_url) > 10 and " " not in callback_url and "://" not in callback_url:
        return callback_url

    return None


def _login_pkce() -> dict:
    """Log in via the PKCE OAuth flow"""
    code_verifier, code_challenge = _pkce_params()
    login_url = _build_login_url(code_challenge)

    print("\n=== Pixiv authentication (PKCE OAuth flow) ===\n")
    print("Open the following URL in your browser and log in to Pixiv.\n")
    print(f"  {login_url}\n")

    # Try to open the browser automatically (on WSL2, use wslview)
    if _open_browser(login_url):
        print("(Browser opened.)\n")
    else:
        print("(Please copy & paste the URL above into your browser manually.)\n")

    print("=" * 60)
    print("[How to obtain the code]")
    print("")
    print("  1. Press F12 in your browser to open DevTools")
    print("  2. Select the 'Network' tab")
    print("  3. Type 'callback' into the 'Filter' box at the top left")
    print("  4. Log in to Pixiv using the URL above")
    print("  5. After logging in, the Network tab will show a request like:")
    print("     callback?state=...&code=XXXXXXXX")
    print("  6. Copy the value of code=XXXXXXXX from that URL")
    print("")
    print("* It is normal to see a page error after logging in.")
    print("  Please check the Network tab in DevTools.")
    print("=" * 60)

    try:
        raw_input = input("\ncode (or callback URL): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)

    code = _extract_code(raw_input)
    if not code:
        print("\nError: Could not extract the authorization code.", file=sys.stderr)
        print("Please check the 'code=' value of the callback request in the Network tab of DevTools.", file=sys.stderr)
        sys.exit(1)

    print("\nFetching token...")
    return _exchange_code(code, code_verifier)


def _print_result_and_save(result: dict) -> None:
    """Display the authentication result and save it to .env"""
    refresh_token = result.get("refresh_token", "")
    if not refresh_token:
        print("Error: Failed to obtain refresh token.", file=sys.stderr)
        sys.exit(1)

    user = result.get("user", {})
    print("\nAuthentication successful!")
    if user:
        print(f"  User name: {user.get('name', 'unknown')}")
        print(f"  Account: {user.get('account', 'unknown')}")
        print(f"  Premium: {'Yes' if user.get('is_premium') else 'No'}")

    _update_env_file("PIXIV_REFRESH_TOKEN", refresh_token)
    print(f"\nSaved refresh token to {ENV_FILE}.")
    print("\nSetup complete! You can start the MCP server with the following command:")
    print("  uv run main.py")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pixiv authentication setup - obtain a refresh token and save it to .env",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python setup_token.py                  # Log in via PKCE OAuth (recommended)
  uv run python setup_token.py --refresh TOKEN  # Refresh a token
  uv run python setup_token.py --token TOKEN    # Save a token directly
        """,
    )
    parser.add_argument(
        "--refresh", "-r",
        metavar="TOKEN",
        help="Refresh an existing refresh token",
    )
    parser.add_argument(
        "--token", "-t",
        help="Manually specify a refresh token and save it to .env",
    )

    args = parser.parse_args()

    # Manual token input
    if args.token:
        _update_env_file("PIXIV_REFRESH_TOKEN", args.token)
        print(f"Saved refresh token to {ENV_FILE}.")
        return

    # Run authentication
    try:
        if args.refresh:
            print("Refreshing token...")
            result = _refresh_token_request(args.refresh)
        else:
            result = _login_pkce()
    except requests.HTTPError as e:
        print(f"\nHTTP error: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    _print_result_and_save(result)


if __name__ == "__main__":
    main()
