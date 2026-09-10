"""End-to-end test for app signup + login pages.

Usage (from backend/, with API running on :8000):
    python -m scripts.test_auth_demo_pages
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000/api/v1"


def _request(method: str, path: str, body: dict | None = None, token: str | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"detail": detail}
        return exc.code, parsed


def main() -> int:
    from app.db.mongo import get_database

    db = get_database()
    software = db.software.find_one(sort=[("created_at", -1)])
    if not software:
        print("FAIL: no software in database")
        return 1

    software_id = str(software["_id"])
    signup = db.pages.find_one({"software_id": software_id, "name": "signup"})
    login = db.pages.find_one({"software_id": software_id, "name": "login"})
    if not signup or not login:
        print("FAIL: run python -m scripts.seed_auth_demo_pages first")
        return 1

    signup_id = str(signup["_id"])
    email = "demo.user@example.com"
    password = "DemoPass123"

    print(f"Software: {software_id}")
    print(f"Signup page: {signup_id}")
    print(f"Login page: {str(login['_id'])}")

    db.users.delete_one({"email": email.lower()})

    print("\n1. App signup…")
    status, body = _request(
        "POST",
        "/auth/app-signup",
        {
            "software_id": software_id,
            "page_id": signup_id,
            "values": {
                "firstName": "Demo",
                "lastName": "User",
                "email": email,
                "password": password,
                "phone": "+15550100",
                "address": "123 Test Street",
                "pincode": "560001",
            },
        },
    )
    if status != 201:
        print(f"FAIL signup HTTP {status}: {body}")
        return 1
    print(f"OK signup — user id {body['user']['id']}, profile keys: {list(body.get('profile', {}).keys())}")

    print("\n2. Login…")
    status, body = _request("POST", "/auth/login", {"email": email, "password": password})
    if status != 200 or not body.get("access_token"):
        print(f"FAIL login HTTP {status}: {body}")
        return 1
    token = body["access_token"]
    print("OK login — received access token")

    print("\n3. Authenticated /auth/me…")
    status, body = _request("GET", "/auth/me", token=token)
    if status != 200:
        print(f"FAIL me HTTP {status}: {body}")
        return 1
    print(f"OK me — {body['user']['name']} <{body['user']['email']}> role={body['user']['role']}")

    profile = db.user_profiles.find_one({"user_id": body["user"]["id"]})
    fields = (profile or {}).get("fields") or {}
    print(f"\nProfile stored: firstName={fields.get('firstName')}, pincode={fields.get('pincode')}")

    print("\nAll tests passed.")
    print(f"Open in browser: http://localhost:4200/run/{software_id}/{signup_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
