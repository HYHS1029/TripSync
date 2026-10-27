"""Create a visible demo in the disposable :8001 API only; never use the real DB."""
from datetime import date, timedelta

import httpx


API = "http://127.0.0.1:8001"
PASSWORD = "correct-horse-battery-123"


def main():
    with httpx.Client(base_url=API, timeout=10) as client:
        assert client.get("/__test__/status").json()["fixture"] == "tripsync-memory-only"

        def login(email):
            response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
            response.raise_for_status()
            return {"Authorization": "Bearer " + response.json()["access_token"]}

        owner = login("traveler@example.com")
        other = login("other@example.com")
        start = date(2027, 2, 3)
        trip = client.post("/trips", headers=owner, json={"name": "東京散步・三天兩夜", "destination": "日本・東京",
            "start_date": start.isoformat(), "end_date": (start + timedelta(days=2)).isoformat(),
            "timezone": "Asia/Tokyo", "currency": "JPY", "description": "示範旅程：一起安排景點、車站和住宿，也一起把旅行開銷記清楚。"}).json()
        base = f"/trips/{trip['id']}"
        invitation = client.post(base + "/invitations", headers=owner).json()
        client.post("/invitations/accept", headers=other, json={"token": invitation["token"]}).raise_for_status()
        people = client.get(base + "/members", headers=owner).json()
        ids = [person["user_id"] for person in people]
        activities = []
        for values in [
            {"title": "東京車站旁住宿", "category": "lodging", "start_time": "08:00", "end_time": "09:00",
             "stay_until": (start + timedelta(days=2)).isoformat(), "location": "入住後，從這裡開始每天的散步。"},
            {"title": "東京車站集合", "category": "station", "start_time": "09:15", "end_time": "09:30", "location": "丸之內中央口集合", "notes": "先確認每個人都到齊，再一起出發。"},
            {"title": "淺草寺與仲見世通", "category": "sight", "start_time": "10:00", "end_time": "12:00", "location": "日本・東京・淺草", "notes": "留一點時間逛小店、吃點心。"},
            {"title": "午餐：和旅伴一起吃", "category": "food", "start_time": "12:30", "end_time": "13:30", "location": "淺草周邊"},
        ]:
            response = client.post(base + "/activities", headers=owner, json={"activity_date": start.isoformat()} | values)
            response.raise_for_status()
            activities.append(response.json())
        for title, amount, payer, category, activity in [
            ("兩晚住宿費", 32000, ids[0], "lodging", activities[0]),
            ("大家的午餐", 4800, ids[1], "food", activities[3]),
            ("機場交通票", 2600, ids[0], "transport", activities[1]),
        ]:
            response = client.post(base + "/expenses", headers=owner, json={"title": title, "expense_date": start.isoformat(),
                "amount_minor": amount, "payer_id": payer, "participant_ids": ids, "category": category, "activity_id": activity["id"]})
            response.raise_for_status()
        print(f"Preview: http://localhost:3001/trips/{trip['id']}")
        print("Disposable fixture only; sample amounts do not represent real purchases.")


if __name__ == "__main__":
    main()
