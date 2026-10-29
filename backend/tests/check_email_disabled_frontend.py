"""Friends-only preview: username registration works while email is unavailable."""
from uuid import uuid4

import httpx

from check_frontend_flow import API, FRONTEND, PASSWORD, PageForms, form_with, get_page, sign_in, submit


def main():
    assert httpx.get(f"{API}/__test__/status").json()["fixture"] == "tripsync-memory-only"
    username = "friends_" + uuid4().hex[:12]
    with httpx.Client(timeout=30) as client:
        page = get_page(client, "/register")
        form = form_with(page, field="confirm_password")
        assert "email" not in form["fields"]
        assert "目前尚未提供忘記密碼功能" in page.text
        created = submit(client, page, form, {"username": username, "password": PASSWORD, "confirm_password": PASSWORD})
        assert created.status_code == 303
        login = get_page(client, created.headers["location"])
        assert "電子郵件可於登入後驗證" not in login.text
        sign_in(client, username)
        account = get_page(client, "/account")
        assert username in account.text and "寄送驗證信" not in account.text
        assert all("email" not in form["fields"] for form in PageForms(account.text).forms)
        verification = client.get(FRONTEND + "/verify-email")
        assert verification.status_code == 404
        assert "確認驗證信箱" not in verification.text
        print("PASS: username-only registration/login and hidden verification UI in the disabled preview")
    for path, body in [
        ("request", {"email": "test@example.com", "password": PASSWORD}),
        ("confirm", {"token": "x" * 43}),
    ]:
        assert httpx.post(f"{API}/auth/email-verification/{path}", json=body).status_code == 404
    print("PASS: direct requests cannot send or confirm emails while the feature is disabled")


if __name__ == "__main__":
    main()
