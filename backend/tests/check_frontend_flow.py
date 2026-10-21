"""Check production HTML forms against the disposable :8001 API and :3001 frontend.

This tests Server Actions through their progressive-enhancement HTTP forms.
It does not execute browser JavaScript or verify visual layout.
"""

from html.parser import HTMLParser
import re
from urllib.parse import urljoin

import httpx


FRONTEND = "http://localhost:3001"
API = "http://127.0.0.1:8001"
PASSWORD = "correct-horse-battery-123"


class PageForms(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.current = None
        self.refresh = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {"attrs": attrs, "fields": set(), "hidden": [], "values": {}, "text": ""}
        elif tag in ("input", "textarea") and self.current is not None and attrs.get("name"):
            self.current["fields"].add(attrs["name"])
            if tag == "input":
                self.current["values"][attrs["name"]] = attrs.get("value", "")
            if attrs.get("type") == "hidden":
                self.current["hidden"].append((attrs["name"], attrs.get("value", "")))
        elif tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            match = re.search(r"url=(.+)", attrs.get("content", ""), re.IGNORECASE)
            if match:
                self.refresh = match.group(1)

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None


def get_page(client, path):
    url = urljoin(FRONTEND, path)
    for _ in range(8):
        response = client.get(url)
        if response.is_redirect:
            url = urljoin(str(response.url), response.headers["location"])
            continue
        refresh = PageForms(response.text).refresh
        if refresh:
            url = urljoin(str(response.url), refresh)
            continue
        return response
    raise AssertionError("Too many redirects")


def form_with(page, *, field=None, text=None):
    for form in PageForms(page.text).forms:
        if field and field in form["fields"]:
            return form
        if text and text in form["text"]:
            return form
    raise AssertionError(f"Form not found: field={field}, text={text}")


def submit(client, page, form, values=None):
    entries = form["hidden"] + list((values or {}).items())
    response = client.post(
        urljoin(str(page.url), form["attrs"].get("action", "")),
        files=[(name, (None, value)) for name, value in entries],
        headers={"Origin": FRONTEND, "Referer": str(page.url)},
    )
    # Chromium treats localhost as a Secure Cookie exception. Emulate only that
    # loopback behavior in this HTTP client; application cookie settings stay intact.
    for cookie in client.cookies.jar:
        if cookie.name == "tripsync_session":
            cookie.secure = False
    return response


def sign_in(client, email):
    page = get_page(client, "/login")
    response = submit(client, page, form_with(page, field="email"), {"email": email, "password": PASSWORD})
    assert response.status_code == 303, response.status_code
    cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "secure" in cookie
    assert "我的帳號" in get_page(client, response.headers["location"]).text


def check_registration():
    values = {
        "email": "new_user@example.com",
        "username": "new_user",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    }
    invalid_cases = [
        ({"email": ""}, "請輸入有效的電子郵件"),
        ({"email": "invalid-email"}, "請輸入有效的電子郵件"),
        ({"username": "ab"}, "請使用 3–50 個英文字母、數字或底線"),
        ({"username": "bad/name"}, "請使用 3–50 個英文字母、數字或底線"),
        ({"username": "x" * 51}, "請使用 3–50 個英文字母、數字或底線"),
        ({"password": "short", "confirm_password": "short"}, "密碼需要 8–128 個字元"),
        ({"password": "x" * 129, "confirm_password": "x" * 129}, "密碼需要 8–128 個字元"),
        ({"confirm_password": "different-password"}, "兩次輸入的密碼不一致"),
        ({"confirm_password": ""}, "兩次輸入的密碼不一致"),
    ]
    with httpx.Client(timeout=20) as client:
        assert 'href="/register"' in get_page(client, "/").text
        assert 'href="/register"' in get_page(client, "/login").text
        page = get_page(client, "/register")
        assert page.status_code == 200 and 'href="/login"' in page.text
        for changes, message in invalid_cases:
            submitted = values | changes
            response = submit(client, page, form_with(page, field="confirm_password"), submitted)
            assert response.status_code == 200, changes
            assert message in response.text, changes
            assert PASSWORD not in response.text, "Password leaked into response HTML"
            form = form_with(response, field="confirm_password")
            assert form["values"]["email"] == submitted["email"]
            assert form["values"]["username"] == submitted["username"]
            assert form["values"]["password"] == form["values"]["confirm_password"] == ""

        for changes in ({"email": "traveler@example.com"}, {"username": "traveler"}):
            response = submit(client, page, form_with(page, field="confirm_password"), values | changes)
            assert response.status_code == 200
            assert "此電子郵件或使用者名稱已被使用" in response.text
            assert PASSWORD not in response.text

        # Retry from an error response and preserve the API's existing whitespace policy.
        submitted = values | {"email": " new_user@example.com ", "username": " new_user ", "password": f" {PASSWORD} "}
        created = submit(client, response, form_with(response, field="confirm_password"), submitted)
        assert created.status_code == 303, created.status_code
        assert created.headers["location"] == "/login?registered=1"
        assert "tripsync_session" not in client.cookies, "Registration should not sign in automatically"
        login_page = get_page(client, created.headers["location"])
        assert "帳號建立成功，請使用新帳號登入" in login_page.text
        sign_in(client, values["email"])
        assert get_page(client, "/register").url.path == "/account"
        print("PASS: registration links, field errors, duplicates, safe retries, success, and new-account login")


def main():
    status = httpx.get(f"{API}/__test__/status", timeout=10).json()
    assert status["fixture"] == "tripsync-memory-only", "Disposable API required"
    assert status["trips"] == 0, "Restart the fixture before running this check"
    check_registration()
    with httpx.Client(timeout=20) as owner, httpx.Client(timeout=20) as other:
        assert get_page(owner, "/trips").url.path == "/login"
        sign_in(owner, "traveler@example.com")
        assert "第一趟旅程，從這裡開始" in get_page(owner, "/trips").text
        page = get_page(owner, "/trips/new")
        values = {
            "name": "北海道滑雪之旅",
            "destination": "日本・北海道",
            "start_date": "2027-02-03",
            "end_date": "2027-02-10",
            "description": "一起滑雪，晚上吃拉麵。",
        }
        invalid = submit(owner, page, form_with(page, field="name"), values | {"end_date": "2027-02-01"})
        assert invalid.status_code == 200
        assert "請檢查欄位內容與日期範圍" in invalid.text
        created = submit(owner, invalid, form_with(invalid, field="name"), values)
        assert created.status_code == 303, created.status_code
        trip_path = created.headers["location"]
        assert re.search(r"/trips/[1-9]\d*$", trip_path)
        detail = get_page(owner, trip_path)
        assert values["name"] in detail.text and values["description"] in detail.text
        assert values["name"] in get_page(owner, trip_path).text  # fresh request
        assert values["name"] in get_page(owner, "/trips").text
        print("PASS: authentication, empty state, validation, create, list, detail, refresh")

        sign_in(other, "other@example.com")
        assert values["name"] not in get_page(other, "/trips").text
        assert "找不到這個旅程" in get_page(other, trip_path).text
        assert "找不到這個旅程" in get_page(other, trip_path + "/edit").text
        print("PASS: second account cannot list, read, or open the edit form")

        edit = get_page(owner, trip_path + "/edit")
        updated_name = "北海道滑雪之旅・更新"
        updated = submit(owner, edit, form_with(edit, field="name"), values | {"name": updated_name, "description": ""})
        assert updated.status_code == 303
        detail = get_page(owner, updated.headers["location"])
        assert updated_name in detail.text and "還沒有旅程說明" in detail.text
        assert updated_name in get_page(owner, "/trips").text
        print("PASS: edit, clear description, and refreshed list")

        deleted = submit(owner, detail, form_with(detail, text="確認刪除"))
        assert deleted.status_code == 303
        assert "第一趟旅程，從這裡開始" in get_page(owner, deleted.headers["location"]).text
        assert "找不到這個旅程" in get_page(owner, trip_path).text
        logout_page = get_page(owner, "/trips")
        logged_out = submit(owner, logout_page, form_with(logout_page, text="登出"))
        assert logged_out.status_code == 303
        assert get_page(owner, "/trips").url.path == "/login"
        status = httpx.get(f"{API}/__test__/status", timeout=10).json()
        assert status["trips"] == 0 and status["memberships"] == 0
        print("PASS: delete, membership cascade, missing trip, logout")


if __name__ == "__main__":
    main()
