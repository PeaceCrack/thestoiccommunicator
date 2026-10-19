"""One-time YouTube sign-in: get a refresh token and store all three YouTube secrets in GitHub.

  python3 youtube_auth.py ~/Downloads/client_secret_XXXX.json

1. Opens Google's consent page in your browser. Sign in, pick the channel
   (The Stoic Communicator), and allow uploads.
2. Checks the channel you picked is the expected one.
3. Pipes YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN straight into
   `gh secret set`, so none of them is printed, saved or pasted anywhere.

Needs the GitHub CLI, logged in (`gh auth login`), run from this repo's folder.
"""

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

EXPECTED_CHANNEL = "UCMN3YKY4HjY4H8enFRvvshg"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
WAIT_S = 300


def read_client(path: Path) -> tuple[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise SystemExit(f"Could not read {path}: {err}") from err
    client = data.get("installed")
    if not client:
        raise SystemExit("That file is not a Desktop app OAuth client. Create one of type 'Desktop app' (SETUP.md).")
    return client["client_id"], client["client_secret"]


def wait_for_code(state: str) -> tuple[http.server.HTTPServer, str, dict]:
    """A one-shot server on a free localhost port. Returns (server, redirect_uri, result dict)."""
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ok = query.get("state", [""])[0] == state and "code" in query
            result.update(code=query.get("code", [""])[0] if ok else "", error=query.get("error", [""])[0])
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = "Signed in. You can close this tab." if ok else "Sign-in failed. Check the terminal."
            self.wfile.write(f"<h2>{msg}</h2>".encode())
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *args) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{server.server_port}"
    return server, redirect, result


def exchange(client_id: str, client_secret: str, code: str, redirect: str, verifier: str) -> dict:
    data = urllib.parse.urlencode({"code": code, "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": redirect, "grant_type": "authorization_code",
                                   "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data), timeout=60) as response:
        return json.loads(response.read())


def my_channel(access_token: str) -> dict:
    url = "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        items = json.loads(response.read()).get("items", [])
    if not items:
        raise SystemExit("That Google account has no YouTube channel. Sign in again and pick the channel.")
    return items[0]


def set_secret(name: str, value: str) -> None:
    result = subprocess.run(["gh", "secret", "set", name], input=value, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"gh secret set {name} failed: {result.stderr.strip()}")
    print(f"  saved GitHub secret {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client_file", type=Path, help="the client_secret_*.json you downloaded from Google Cloud")
    parser.add_argument("--expect-channel", default=EXPECTED_CHANNEL)
    args = parser.parse_args()

    client_id, client_secret = read_client(args.client_file)
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    server, redirect, result = wait_for_code(state)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent select_account", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    print("Opening Google sign-in. If no browser opens, visit:\n" + url)
    webbrowser.open(url)
    timer = threading.Timer(WAIT_S, server.shutdown)
    timer.start()
    server.serve_forever()
    timer.cancel()
    if not result.get("code"):
        raise SystemExit(f"No authorization code received ({result.get('error') or 'timed out'}).")

    tokens = exchange(client_id, client_secret, result["code"], redirect, verifier)
    if "refresh_token" not in tokens:
        raise SystemExit("Google returned no refresh token. Remove the app at myaccount.google.com/permissions and retry.")
    channel = my_channel(tokens["access_token"])
    print(f"Signed in to channel: {channel['snippet']['title']} ({channel['id']})")
    if args.expect_channel and channel["id"] != args.expect_channel:
        raise SystemExit(f"That is not {args.expect_channel}. Run again and choose The Stoic Communicator channel.")
    for name, value in (("YT_CLIENT_ID", client_id), ("YT_CLIENT_SECRET", client_secret),
                        ("YT_REFRESH_TOKEN", tokens["refresh_token"])):
        set_secret(name, value)
    print("Done. YouTube uploads are ready.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
