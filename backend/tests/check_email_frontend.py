"""Verify production Server Actions with disposable :8001 data and local Mailpit."""
import re
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from check_frontend_flow import API, FRONTEND, PASSWORD, form_with, get_page, sign_in, submit

MAILPIT = "http://127.0.0.1:8025"


def main():
    assert httpx.get(f"{API}/__test__/status").json()["fixture"] == "tripsync-memory-only"
    username = "email_" + uuid4().hex[:12]
    email = username + "@example.com"
    result = httpx.post(f"{API}/users", json={"username": username, "password": PASSWORD})
    assert result.status_code == 201 and result.json()["email"] is None
    with httpx.Client(timeout=30) as owner, httpx.Client(timeout=30) as fresh_browser:
        sign_in(owner, username)
        page = get_page(owner, "/account")
        assert "綁定並驗證電子郵件" in page.text
        wrong = submit(owner, page, form_with(page, field="email"), {"email": email, "password": "incorrect-password"})
        assert "密碼不正確" in wrong.text
        assert PASSWORD not in wrong.text
        response = submit(owner, wrong, form_with(wrong, field="email"), {"email": email, "password": PASSWORD})
        assert response.status_code == 200 and "驗證信已寄出" in response.text
        assert PASSWORD not in response.text
        messages = httpx.get(f"{MAILPIT}/api/v1/messages").json()["messages"]
        message = next(item for item in messages if any(address["Address"] == email for address in item["To"]))
        content = httpx.get(f'{MAILPIT}/api/v1/message/{message["ID"]}').json()
        link = re.search(r"https?://[^\s]+/verify-email#[A-Za-z0-9_-]{43}", content["Text"]).group(0)
        assert link.startswith(FRONTEND + "/verify-email#")
        token = urlsplit(link).fragment
        assert token not in response.text
        assert httpx.post(f"{API}/auth/login", json={"identifier": email, "password": PASSWORD}).status_code == 401

        page = get_page(fresh_browser, "/verify-email")
        assert token not in page.text
        continued = submit(fresh_browser, page, form_with(page, field="token"), {"token": token})
        assert continued.status_code == 303 and continued.headers["location"] == "/login?next=verify-email"
        cookie = continued.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie and "secure" in cookie and "path=/verify-email" in cookie
        login_page = get_page(fresh_browser, continued.headers["location"])
        assert token not in login_page.text
        sign_in(fresh_browser, username, next_value="verify-email")
        page = get_page(fresh_browser, "/verify-email")
        assert username in page.text
        verified = submit(fresh_browser, page, form_with(page, field="token"))
        assert verified.status_code == 303 and verified.headers["location"] == "/account?email_verified=1"
        page = get_page(fresh_browser, "/account")
        assert "已驗證" in page.text and email in page.text
        assert "tripsync_email_verification" not in fresh_browser.cookies
        print("PASS: SMTP delivery, reauthentication, protected login continuation, and verified account UI")

        page = get_page(owner, "/verify-email")
        replay = submit(owner, page, form_with(page, field="token"), {"token": token})
        assert replay.status_code == 200 and "已被使用" in replay.text
        assert token not in replay.headers.get("location", "")
        submit(fresh_browser, page := get_page(fresh_browser, "/account"), form_with(page, text="登出"))
        sign_in(fresh_browser, email)
        print("PASS: consumed links are rejected and email login works after verification")


if __name__ == "__main__":
    main()
