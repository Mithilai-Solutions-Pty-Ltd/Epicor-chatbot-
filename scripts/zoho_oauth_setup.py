"""
============================================================
Zoho OAuth Setup Helper (run ONCE to get your refresh token)
============================================================
STEP-BY-STEP:
  1. Go to https://api-console.zoho.in
  2. Click "Add Client" → choose "Server-based Applications"
  3. Fill in:
       Client Name:    BOTZI
       Homepage URL:   https://botzi-api.onrender.com
       Redirect URI:   https://botzi-api.onrender.com/zoho/callback
                       (or http://localhost:8000/zoho/callback for local)
  4. Copy your CLIENT_ID and CLIENT_SECRET into .env
  5. Run this script:
       python scripts/zoho_oauth_setup.py
  6. It will open a browser URL – paste it in Chrome, log in,
     and you'll get an authorization code.
  7. Paste the code here and this script exchanges it for a
     long-lived refresh token.
  8. Copy the refresh token into your .env ZOHO_REFRESH_TOKEN
============================================================
"""

import os
import sys
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.environ.get("ZOHO_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET", "")
REDIRECT_URI  = "https://botzi-api.onrender.com/zoho/callback"
SCOPES        = "WorkDrive.files.READ,WorkDrive.folders.READ,WorkDrive.team.READ"
ACCOUNTS_URL  = os.environ.get("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.in/oauth/v2")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET must be set in your .env")
    sys.exit(1)


def step1_get_authorization_url():
    """Generate the authorization URL and open it in the browser."""
    auth_url = (
        f"{ACCOUNTS_URL}/auth"
        f"?scope={SCOPES}"
        f"&client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&access_type=offline"
        f"&redirect_uri={REDIRECT_URI}"
    )
    print("\n" + "="*60)
    print("STEP 1: Open this URL in your browser and log in:")
    print("="*60)
    print(auth_url)
    print("="*60)
    print("\nAfter logging in, Zoho will redirect to:")
    print(f"  {REDIRECT_URI}?code=<AUTHORIZATION_CODE>")
    print("\nCopy the 'code' parameter from the URL.")
    try:
        webbrowser.open(auth_url)
        print("(Browser opened automatically)")
    except Exception:
        print("(Could not open browser – please copy the URL manually)")


def step2_exchange_code_for_token(code: str):
    """Exchange authorization code for refresh token."""
    resp = requests.post(
        f"{ACCOUNTS_URL}/token",
        data={
            "grant_type":    "authorization_code",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri":  REDIRECT_URI,
            "code":          code.strip(),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "refresh_token" not in data:
        print(f"❌ Error: {data}")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ SUCCESS! Copy these values into your .env file:")
    print("="*60)
    print(f"ZOHO_REFRESH_TOKEN={data['refresh_token']}")
    if data.get("access_token"):
        print(f"\n(Access token for testing: {data['access_token'][:20]}...)")
    print("="*60)
    return data["refresh_token"]


def find_team_folder_id(access_token: str):
    """
    Helper: list your WorkDrive teams and team folders
    so you can find ZOHO_TEAM_FOLDER_ID.
    """
    base = os.environ.get("ZOHO_WORKDRIVE_URL", "https://workdrive.zoho.in/api/v1")
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

    try:
        resp = requests.get(f"{base}/users/me/teams", headers=headers, timeout=20)
        teams = resp.json().get("data", [])
        print("\n📁 Your WorkDrive Teams:")
        for team in teams:
            tid  = team.get("id")
            name = team.get("attributes", {}).get("name", "")
            print(f"   Team: {name} | ID: {tid}")

            # List team folders
            r2 = requests.get(f"{base}/teams/{tid}/folders", headers=headers, timeout=20)
            folders = r2.json().get("data", [])
            for folder in folders:
                fid  = folder.get("id")
                fname = folder.get("attributes", {}).get("name", "")
                print(f"     📂 Folder: {fname} | ID: {fid}")
                if "training" in fname.lower():
                    print(f"     ⭐ THIS looks like your target folder!")
                    print(f"        Set ZOHO_TEAM_FOLDER_ID={fid}")
    except Exception as e:
        print(f"Could not list teams: {e}")


if __name__ == "__main__":
    step1_get_authorization_url()
    print()
    code = input("Paste the authorization code here: ").strip()
    if not code:
        print("❌ No code provided")
        sys.exit(1)

    token = step2_exchange_code_for_token(code)

    print("\nNow finding your Team Folder ID…")
    # Get a temporary access token to list folders
    resp = requests.post(
        f"{ACCOUNTS_URL}/token",
        data={
            "grant_type":    "refresh_token",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": token,
        },
        timeout=20,
    )
    access_token = resp.json().get("access_token", "")
    if access_token:
        find_team_folder_id(access_token)

    print("\n✅ OAuth setup complete! Update your .env and deploy.")
