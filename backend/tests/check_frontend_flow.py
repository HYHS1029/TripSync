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
    values = values or {}
    # Emulate updating an existing hidden input (the browser's fragment reader),
    # rather than sending both its empty SSR value and the supplied value.
    entries = [(name, value) for name, value in form["hidden"] if name not in values] + list(values.items())
    response = client.post(
        urljoin(str(page.url), form["attrs"].get("action", "")),
        files=[(name, (None, value)) for name, value in entries],
        headers={"Origin": FRONTEND, "Referer": str(page.url)},
    )
    # Chromium treats localhost as a Secure Cookie exception. Emulate only that
    # loopback behavior in this HTTP client; application cookie settings stay intact.
    for cookie in client.cookies.jar:
        if cookie.name in ("tripsync_session", "tripsync_invitation"):
            cookie.secure = False
    return response


def sign_in(client, email, *, next_value=None):
    page = get_page(client, "/login")
    values = {"email": email, "password": PASSWORD}
    if next_value is not None:
        values["next"] = next_value
    response = submit(client, page, form_with(page, field="email"), values)
    assert response.status_code == 303, response.status_code
    cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "secure" in cookie
    if next_value is not None:
        assert response.headers["location"] == "/account", "External redirect must be ignored"
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
        submitted = values | {"email": " new_user@example.com ", "username": " new_user ", "password": f" {PASSWORD} ", "next": "https://untrusted.invalid/"}
        created = submit(client, response, form_with(response, field="confirm_password"), submitted)
        assert created.status_code == 303, created.status_code
        assert created.headers["location"] == "/login?registered=1"
        assert "tripsync_session" not in client.cookies, "Registration should not sign in automatically"
        login_page = get_page(client, created.headers["location"])
        assert "帳號建立成功，請使用新帳號登入" in login_page.text
        sign_in(client, values["email"], next_value="https://untrusted.invalid/")
        assert get_page(client, "/register").url.path == "/account"
        print("PASS: registration links, field errors, duplicates, safe retries, success, and new-account login")


def invitation_link(client, trip_path):
    page = get_page(client, trip_path + "/members")
    response = submit(client, page, form_with(page, text="建立邀請連結"))
    assert response.status_code == 200
    match = re.search(r"/join#([A-Za-z0-9_-]{43})", response.text)
    assert match, "Invitation not generated"
    token = match.group(1)
    assert token not in get_page(client, trip_path + "/members").text
    return token


def accept_link(client, token):
    page = get_page(client, "/join")
    return submit(client, page, form_with(page, field="token"), {"token": token})


def check_collaboration(owner, other, trip_path):
    activity_values = {"title": "小樽運河散步", "activity_date": "2027-02-04", "start_time": "10:00", "end_time": "11:30", "location": "小樽運河", "notes": "北側集合 <script>alert(1)</script>"}
    page = get_page(owner, trip_path + "/activities/new?day=2027-02-04")
    invalid = submit(owner, page, form_with(page, field="title"), activity_values | {"end_time": "08:00"})
    assert "請確認日期在旅程範圍內" in invalid.text
    created = submit(owner, invalid, form_with(invalid, field="title"), activity_values)
    assert created.status_code == 303
    day_path = created.headers["location"]
    detail = get_page(owner, day_path)
    assert activity_values["title"] in detail.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in detail.text
    assert "<script>alert(1)</script>" not in detail.text
    assert detail.headers["referrer-policy"] == "no-referrer"
    assert detail.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in detail.headers["content-security-policy"]
    activity_path = re.search(rf"{re.escape(trip_path)}/activities/[1-9]\d*/edit", detail.text).group(0)
    assert "小樽運河散步" not in get_page(owner, trip_path).text  # another day
    assert "每天，都有新的期待" in get_page(owner, trip_path + "?day=invalid").text
    print("PASS: daily activities, date navigation, time validation, escaped notes, response headers")

    token = invitation_link(owner, trip_path)
    # A cross-origin POST cannot use a valid invitation on behalf of this user.
    join_page = get_page(other, "/join")
    join_form = form_with(join_page, field="token")
    entries = [(name, value) for name, value in join_form["hidden"] if name != "token"] + [("token", token)]
    blocked = other.post(str(join_page.url), files=[(name, (None, value)) for name, value in entries], headers={"Origin": "https://untrusted.invalid", "Referer": "https://untrusted.invalid/"})
    assert blocked.status_code in (400, 403, 500), "Cross-origin action must be rejected"
    assert httpx.get(f"{API}/__test__/status", timeout=10).json()["memberships"] == 1
    logout = get_page(other, "/account")
    submit(other, logout, form_with(logout, text="登出"))
    pending = accept_link(other, token)
    assert pending.status_code == 303 and pending.headers["location"] == "/login?next=join"
    cookie = pending.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie and "secure" in cookie and "max-age=900" in cookie
    login = get_page(other, pending.headers["location"])
    assert token not in login.text and 'href="/register?next=join"' in login.text
    logged_in = submit(other, login, form_with(login, field="email"), {"email": "other@example.com", "password": PASSWORD})
    assert logged_in.status_code == 303 and logged_in.headers["location"] == "/join"
    confirm = get_page(other, "/join")
    joined = submit(other, confirm, form_with(confirm, field="token"))
    assert joined.status_code == 303 and joined.headers["location"] == trip_path
    assert "tripsync_invitation" not in other.cookies
    assert activity_values["title"] in get_page(other, day_path).text
    edit = get_page(other, activity_path)
    edit_error = submit(other, edit, form_with(edit, field="title"), activity_values | {"end_time": "08:00"})
    assert edit_error.status_code == 200 and "請確認日期在旅程範圍內" in edit_error.text
    updated = submit(other, edit_error, form_with(edit_error, field="title"), activity_values | {"title": "旅伴更新的運河散步", "notes": ""})
    assert updated.status_code == 303
    assert "旅伴更新的運河散步" in get_page(owner, day_path).text
    members = get_page(other, trip_path + "/members")
    assert "建立邀請連結" not in members.text and "移除成員" not in members.text
    left = submit(other, members, form_with(members, text="確認退出旅程"))
    assert left.status_code == 303
    assert "找不到這個旅程" in get_page(other, trip_path).text
    replay = accept_link(other, token)
    assert replay.status_code == 200 and "邀請已失效" in replay.text
    print("PASS: private invite cookie, login continuation, member collaboration, leave, replay prevention")

    token = invitation_link(owner, trip_path)
    assert accept_link(other, token).status_code == 303
    members = get_page(owner, trip_path + "/members")
    removed = submit(owner, members, form_with(members, text="確認移除成員"))
    assert removed.status_code == 200
    assert "找不到這個旅程" in get_page(other, trip_path + "/members").text
    assert "找不到這個旅程" in get_page(other, activity_path).text
    revoked_token = invitation_link(owner, trip_path)
    members = get_page(owner, trip_path + "/members")
    revoked = submit(owner, members, form_with(members, text="確認撤銷邀請"))
    assert revoked.status_code == 200
    assert "邀請已失效" in accept_link(other, revoked_token).text
    print("PASS: owner removal, immediate page restrictions, invitation revocation")

    # A new account follows the same invite across registration without URL secrets.
    token = invitation_link(owner, trip_path)
    with httpx.Client(timeout=20) as guest:
        pending = accept_link(guest, token)
        assert pending.status_code == 303
        page = get_page(guest, "/register?next=join")
        created = submit(guest, page, form_with(page, field="confirm_password"), {"email": "invitee@example.com", "username": "invitee", "password": PASSWORD, "confirm_password": PASSWORD})
        assert created.status_code == 303 and created.headers["location"] == "/login?registered=1&next=join"
        page = get_page(guest, created.headers["location"])
        login = submit(guest, page, form_with(page, field="email"), {"email": "invitee@example.com", "password": PASSWORD})
        assert login.status_code == 303 and login.headers["location"] == "/join"
        page = get_page(guest, "/join")
        joined = submit(guest, page, form_with(page, field="token"))
        assert joined.status_code == 303 and joined.headers["location"] == trip_path
        page = get_page(guest, trip_path + "/members")
        assert submit(guest, page, form_with(page, text="確認退出旅程")).status_code == 303
    detail = get_page(owner, day_path)
    deleted = submit(owner, detail, form_with(detail, text="確認刪除活動"))
    assert deleted.status_code == 303
    assert "旅伴更新的運河散步" not in get_page(owner, day_path).text
    print("PASS: registration continuation and activity deletion")


def check_expenses(owner, other, trip_path):
    # Set up membership through the existing browser forms.
    token = invitation_link(owner, trip_path)
    assert accept_link(other, token).status_code == 303
    page = get_page(owner, trip_path + "/expenses/new")
    participant_ids = re.findall(r'name="participant_ids"[^>]*value="(\d+)"', page.text)
    assert len(participant_ids) == 2, participant_ids
    values = {"title": "共同住宿費", "expense_date": "2027-01-15", "category": "lodging", "amount": "100.01",
              "payer_id": participant_ids[0], "split_mode": "equal", "activity_id": "", "notes": "先付訂金"}

    def expense_submit(page, changes=None, custom_entries=None):
        submitted = values | (changes or {})
        form = form_with(page, field="title")
        entries = [(name, value) for name, value in form["hidden"] if name not in submitted]
        entries += list(submitted.items()) + [("participant_ids", value) for value in participant_ids]
        entries += custom_entries or []
        return owner.post(str(page.url), files=[(name, (None, value)) for name, value in entries], headers={"Origin": FRONTEND, "Referer": str(page.url)})

    invalid = expense_submit(page, {"amount": "100.001"})
    assert invalid.status_code == 200 and "最多 2 位小數" in invalid.text
    created = expense_submit(invalid)
    assert created.status_code == 303, created.text[:500]
    ledger = get_page(owner, trip_path + "/expenses")
    assert "共同住宿費" in ledger.text and "50.01" in ledger.text and "50.00" in ledger.text
    assert "共同住宿費" in get_page(other, trip_path + "/expenses").text
    assert "編輯費用" not in get_page(other, trip_path + "/expenses").text
    edit_path = re.search(rf"{re.escape(trip_path)}/expenses/\d+/edit", ledger.text).group(0)
    edit = get_page(owner, edit_path)
    custom = expense_submit(edit, {"amount": "100.00", "split_mode": "custom"},
                            [(f"share_{participant_ids[0]}", "25.00"), (f"share_{participant_ids[1]}", "75.00")])
    assert custom.status_code == 303
    ledger = get_page(owner, trip_path + "/expenses")
    assert "自訂金額" in ledger.text and "75.00" in ledger.text
    settlement = get_page(owner, trip_path + "/settlements/new")
    settled = submit(owner, settlement, form_with(settlement, field="amount"), {
        "sender_id": participant_ids[1], "recipient_id": participant_ids[0], "amount": "25.00",
        "settled_on": "2027-02-05", "notes": "部分還款"})
    assert settled.status_code == 303, settled.text[:500]
    ledger = get_page(owner, trip_path + "/expenses")
    assert "部分還款" in ledger.text and "50.00" in ledger.text
    bad_currency = get_page(owner, trip_path + "/edit")
    blocked = submit(owner, bad_currency, form_with(bad_currency, field="name"), {
        "name": "北海道滑雪之旅", "destination": "日本・北海道", "start_date": "2027-02-03", "end_date": "2027-02-10",
        "description": "Skiing with friends", "timezone": "Asia/Tokyo", "currency": "JPY"})
    assert blocked.status_code == 200 and "無法更換記帳幣別" in blocked.text
    members = get_page(other, trip_path + "/members")
    assert submit(other, members, form_with(members, text="確認退出旅程")).status_code == 303
    assert "已離開" in get_page(owner, trip_path + "/expenses").text
    assert "找不到這個旅程" in get_page(other, trip_path + "/expenses").text
    print("PASS: expense forms, decimal validation, deterministic split, custom edit, member permissions, partial repayment, currency guard and departed-member history")


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
        check_collaboration(owner, other, trip_path)
        check_expenses(owner, other, trip_path)

        edit = get_page(owner, trip_path + "/edit")
        invalid_edit = submit(owner, edit, form_with(edit, field="name"), values | {"end_date": "2027-02-01"})
        assert invalid_edit.status_code == 200 and "請檢查欄位內容與日期範圍" in invalid_edit.text
        updated_name = "北海道滑雪之旅・更新"
        updated = submit(owner, invalid_edit, form_with(invalid_edit, field="name"), values | {"name": updated_name, "description": ""})
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
        assert all(status[key] == 0 for key in ("trips", "memberships", "activities", "invitations"))
        print("PASS: delete, membership cascade, missing trip, logout")


if __name__ == "__main__":
    main()
