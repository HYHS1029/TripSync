"""Check running local dev (:3000) and production (:3001) login guards.

Run after setup_dev_login.py, a production build, and both frontend starts.
Only signs in to the dedicated developer account; creates no trip data.
"""

import json
from pathlib import Path

from dotenv import dotenv_values
import httpx

from check_frontend_flow import PageForms


def main():
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    secret = dotenv_values(frontend / ".env.development.local", interpolate=False)["TRIPSYNC_DEV_LOGIN_PASSWORD"]
    assert secret
    with httpx.Client(timeout=30) as client:
        dev = client.get("http://localhost:3000/login")
        assert dev.status_code == 200
        form = next(form for form in PageForms(dev.text).forms if "開發者快速登入" in form["text"])
        assert secret not in dev.text
        assert "password" not in form["fields"] and "email" not in form["fields"]
        response = client.post(
            "http://localhost:3000/login",
            files=[(name, (None, value)) for name, value in form["hidden"]],
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/account"
        cookie = response.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie and "samesite=lax" in cookie
        assert "developer@example.com" in client.get("http://localhost:3000/account").text
        print("PASS: one-click login uses the persistent developer account and an HttpOnly session.")

    with httpx.Client(timeout=30) as client:
        prod = client.get("http://localhost:3001/login")
        assert prod.status_code == 200 and "開發者快速登入" not in prod.text
        assert secret not in prod.text
        manifest = json.loads((frontend / ".next/server/server-reference-manifest.json").read_text())
        action_id = next(key for key, value in manifest["node"].items() if value.get("exportedName") == "developmentLogin")
        # Exercise the exported action directly even though no button is rendered.
        response = client.post(
            "http://localhost:3001/login",
            content=json.dumps([{}, None]),
            headers={"Origin": "http://localhost:3001", "Next-Action": action_id, "Content-Type": "text/plain;charset=UTF-8"},
        )
        assert response.status_code == 200
        assert "開發者快速登入僅供已設定的本機開發環境使用。" in response.text
        assert "tripsync_session" not in response.headers.get("set-cookie", "")
        print("PASS: production hides the shortcut and rejects direct action invocation.")

    assert not any(secret in file.read_text(encoding="utf-8") for file in (frontend / ".next/static").rglob("*.js"))
    print("PASS: the generated password is absent from rendered HTML and browser bundles.")


if __name__ == "__main__":
    main()
