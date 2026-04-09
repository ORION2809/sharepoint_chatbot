"""
Login script for SharePoint Chatbot.
Run this ONCE to authenticate. Token is cached for future use.
Uses authorization code flow with a local redirect server.
"""
import json
import sys
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import httpx

import config

TOKEN_CACHE_FILE = Path(__file__).parent / ".token_cache.json"
SCOPES = ["Sites.Read.All", "Files.Read.All"]
REDIRECT_PORT = 8400
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"

auth_code_result = {"code": None, "error": None}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            auth_code_result["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Login successful! You can close this tab.</h2>")
        else:
            error = params.get("error", ["unknown"])[0]
            desc = params.get("error_description", [""])[0]
            auth_code_result["error"] = f"{error}: {desc}"
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>Error: {error}</h2><p>{desc}</p>".encode())

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


def main():
    # Check if already logged in
    if TOKEN_CACHE_FILE.exists():
        try:
            data = json.loads(TOKEN_CACHE_FILE.read_text())
            if data.get("access_token") and data.get("refresh_token"):
                # Try refreshing
                token = refresh_token(data["refresh_token"])
                if token:
                    print("Already logged in (token refreshed).")
                    test_access(token)
                    return
        except Exception:
            pass

    # Build auth URL
    scope_str = " ".join(SCOPES)
    auth_url = (
        f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/v2.0/authorize?"
        + urllib.parse.urlencode({
            "client_id": config.AZURE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": scope_str + " offline_access",
            "response_mode": "query",
        })
    )

    print()
    print("=" * 60)
    print("  SHAREPOINT CHATBOT - LOGIN")
    print("=" * 60)
    print()
    print("  Opening browser for sign-in...")
    print(f"  (If it doesn't open, go to: {auth_url[:80]}...)")
    print()

    # Start local server BEFORE opening browser
    server = HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server.timeout = 120

    webbrowser.open(auth_url)

    print("  Waiting for sign-in callback...")
    server.handle_request()
    server.server_close()

    if auth_code_result["error"]:
        print(f"\n  ERROR: {auth_code_result['error']}")
        print()
        print("  If you see 'redirect_uri mismatch', add this redirect URI")
        print("  in Azure Portal > App registrations > SharepointIntegration >")
        print(f"  Authentication > Add platform > Web > Redirect URI: {REDIRECT_URI}")
        sys.exit(1)

    if not auth_code_result["code"]:
        print("\n  ERROR: No auth code received. Try again.")
        sys.exit(1)

    # Exchange code for tokens
    print("  Exchanging code for tokens...")
    token_url = f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": config.AZURE_CLIENT_ID,
        "client_secret": config.AZURE_CLIENT_SECRET,
        "code": auth_code_result["code"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": scope_str + " offline_access",
    }

    resp = httpx.post(token_url, data=data, timeout=15)
    result = resp.json()

    if "access_token" not in result:
        print(f"\n  Token exchange failed: {result.get('error_description', result)}")
        sys.exit(1)

    # Save tokens
    TOKEN_CACHE_FILE.write_text(json.dumps({
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "expires_in": result.get("expires_in", 3600),
    }))

    print("  Login successful! Token cached.")
    test_access(result["access_token"])


def refresh_token(rt: str) -> str | None:
    """Refresh the access token using the stored refresh token."""
    token_url = f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/v2.0/token"
    scope_str = " ".join(SCOPES)
    data = {
        "client_id": config.AZURE_CLIENT_ID,
        "client_secret": config.AZURE_CLIENT_SECRET,
        "refresh_token": rt,
        "grant_type": "refresh_token",
        "scope": scope_str + " offline_access",
    }
    try:
        resp = httpx.post(token_url, data=data, timeout=15)
        result = resp.json()
        if "access_token" in result:
            TOKEN_CACHE_FILE.write_text(json.dumps({
                "access_token": result["access_token"],
                "refresh_token": result.get("refresh_token", rt),
                "expires_in": result.get("expires_in", 3600),
            }))
            return result["access_token"]
    except Exception:
        pass
    return None


def test_access(token: str):
    """Quick test that the token works for SharePoint."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    print("\n  Testing SharePoint access...")
    try:
        r = httpx.get(
            f"https://graph.microsoft.com/v1.0/sites/{config.SHAREPOINT_HOSTNAME}:/",
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  Site: {data.get('displayName', '?')}")
            print(f"  URL: {data.get('webUrl', '?')}")
            print()
            print("  === ALL GOOD! Run 'python main.py' to start the chatbot. ===")
        else:
            print(f"  Status: {r.status_code}")
            print(f"  Error: {r.text[:300]}")
    except Exception as e:
        print(f"  Network error: {e}")


if __name__ == "__main__":
    main()
