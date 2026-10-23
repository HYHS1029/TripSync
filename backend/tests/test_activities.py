from datetime import time
from unittest.mock import patch
from test_trips import TripTestCase

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.activity import Activity


class ActivityTests(TripTestCase):
    def setUp(self):
        super().setUp()
        self.trip = self.create()
        self.add_member(self.trip["id"])
        self.url = f"/trips/{self.trip['id']}/activities"
        self.activity = {"title": "Ski lesson", "activity_date": "2027-02-04", "start_time": "09:00", "end_time": "12:00", "location": "Ski resort", "notes": "Meet at entrance"}

    def add_activity(self, user=0, **changes):
        response = self.client.post(self.url, json=self.activity | changes, headers=self.headers[user])
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_members_can_create_edit_and_delete_shared_activities(self):
        item = self.add_activity(user=1)
        self.assertEqual(item["created_by"], self.ids[1])
        url = self.url + f"/{item['id']}"
        response = self.client.put(url, json=self.activity | {"title": "Updated", "location": "", "notes": ""}, headers=self.headers[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Updated")
        self.assertIsNone(response.json()["location"])
        self.assertIsNone(response.json()["notes"])
        self.assertEqual(response.json()["created_by"], self.ids[1])
        self.assertEqual(self.client.delete(url, headers=self.headers[1]).status_code, 204)
        self.assertEqual(self.client.get(self.url, headers=self.headers[0]).json(), [])

    def test_authentication_and_membership_required_for_every_operation(self):
        item = self.add_activity()
        for headers, expected in [({}, 401), (self.headers[2], 404)]:
            for method, suffix, kwargs in [("get", "", {}), ("get", f"/{item['id']}", {}), ("post", "", {"json": self.activity}),
                                            ("put", f"/{item['id']}", {"json": self.activity}), ("delete", f"/{item['id']}", {})]:
                with self.subTest(method=method, expected=expected):
                    self.assertEqual(getattr(self.client, method)(self.url + suffix, headers=headers, **kwargs).status_code, expected)

    def test_removed_member_cannot_write(self):
        item = self.add_activity()
        self.client.delete(f"/trips/{self.trip['id']}/members/{self.ids[1]}", headers=self.headers[0])
        self.assertEqual(self.client.put(self.url + f"/{item['id']}", json=self.activity, headers=self.headers[1]).status_code, 404)
        self.assertEqual(self.client.post(self.url, json=self.activity, headers=self.headers[1]).status_code, 404)

    def test_ids_are_scoped_to_parent_trip(self):
        item = self.add_activity()
        other = self.create(name="Another trip")
        url = f"/trips/{other['id']}/activities/{item['id']}"
        self.assertEqual(self.client.put(url, json=self.activity, headers=self.headers[0]).status_code, 404)
        self.assertEqual(self.client.delete(url, headers=self.headers[0]).status_code, 404)

    def test_optional_times_and_empty_fields(self):
        item = self.add_activity(start_time=None, end_time=None, location="  ", notes="")
        for field in ["start_time", "end_time", "location", "notes"]:
            self.assertIsNone(item[field])

    def test_invalid_input_and_time_ranges_are_rejected(self):
        cases = [{"title": " "}, {"title": "x" * 101}, {"location": "x" * 201}, {"notes": "x" * 2001},
                 {"activity_date": "2027-02-02"}, {"activity_date": "2027-02-11"}, {"activity_date": "2027-02-30"},
                 {"start_time": None}, {"end_time": "08:00"}, {"start_time": "09:00:01"},
                 {"start_time": "09:00+08:00"}, {"created_by": self.ids[2]}, {"trip_id": 99}]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post(self.url, json=self.activity | changes, headers=self.headers[0]).status_code, 422)

    def test_list_orders_by_day_then_time_with_untimed_items_last(self):
        untimed = self.add_activity(start_time=None, end_time=None)
        late = self.add_activity(start_time="15:00", end_time=None)
        early = self.add_activity()
        previous = self.add_activity(activity_date="2027-02-03")
        response = self.client.get(self.url, headers=self.headers[1])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual([row["id"] for row in response.json()], [previous["id"], early["id"], late["id"], untimed["id"]])

    def test_trip_dates_cannot_exclude_existing_activities(self):
        self.add_activity()
        url = f"/trips/{self.trip['id']}"
        for changes in [{"start_date": "2027-02-05"}, {"end_date": "2027-02-03"}]:
            self.assertEqual(self.client.patch(url, json=changes, headers=self.headers[0]).status_code, 422)
        self.assertEqual(self.client.patch(url, json={"start_date": "2027-02-01", "end_date": "2027-02-12"}, headers=self.headers[0]).status_code, 200)

    def test_update_also_checks_date_and_times(self):
        item = self.add_activity()
        for changes in [{"activity_date": "2028-01-01"}, {"end_time": "07:00"}]:
            self.assertEqual(self.client.put(self.url + f"/{item['id']}", json=self.activity | changes, headers=self.headers[0]).status_code, 422)
        self.assertEqual(self.client.get(self.url, headers=self.headers[0]).json()[0]["title"], self.activity["title"])

    def test_activity_limit_and_deletion_release_capacity(self):
        first = self.add_activity()
        self.add_activity()
        with patch("app.api.activities.MAX_ACTIVITIES", 2):
            self.assertEqual(self.client.post(self.url, json=self.activity, headers=self.headers[0]).status_code, 409)
            self.client.delete(self.url + f"/{first['id']}", headers=self.headers[0])
            self.add_activity()

    def test_database_also_checks_time_range(self):
        item = self.add_activity()
        with Session(self.engine) as db:
            db.get(Activity, item["id"]).end_time = time(8)
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_trip_deletion_cascades_activities(self):
        self.add_activity()
        self.client.delete(f"/trips/{self.trip['id']}", headers=self.headers[0])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Activity)), 0)
