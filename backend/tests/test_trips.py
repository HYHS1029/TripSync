"""Trip API tests with real SQL constraints in isolated, in-memory SQLite."""

import os
import unittest

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-test-only-key-not-for-real-use-123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models.trip import Trip, TripMember
from app.models.user import User


class TripTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(cls.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        cls.password_hash = hash_password("trips-test-password-123")
        get_settings.cache_clear()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        get_settings.cache_clear()

    def setUp(self):
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            users = [User(email=f"user{i}@example.com", username=f"user{i}", password_hash=self.password_hash) for i in range(3)]
            db.add_all(users)
            db.commit()
            self.ids = [user.id for user in users]
        self.headers = [{"Authorization": f"Bearer {create_access_token(user_id)}"} for user_id in self.ids]

        def test_db():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.client = TestClient(app, raise_server_exceptions=False)
        self.payload = {
            "name": "Hokkaido ski trip",
            "destination": "Hokkaido, Japan",
            "start_date": "2027-02-03",
            "end_date": "2027-02-10",
            "description": "Skiing with friends",
        }

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def create(self, user=0, **changes):
        response = self.client.post("/trips", json=self.payload | changes, headers=self.headers[user])
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def add_member(self, trip_id, user=1):
        with Session(self.engine) as db:
            db.add(TripMember(trip_id=trip_id, user_id=self.ids[user]))
            db.commit()

class TripTests(TripTestCase):
    def test_create_assigns_authenticated_owner_and_membership(self):
        trip = self.create()
        self.assertEqual(trip["owner_id"], self.ids[0])
        self.assertEqual(trip["name"], self.payload["name"])
        self.assertEqual(set(trip), {"id", "name", "destination", "start_date", "end_date", "description", "owner_id", "created_at", "updated_at"})
        with Session(self.engine) as db:
            self.assertIsNotNone(db.get(TripMember, (trip["id"], self.ids[0])))

    def test_complete_crud_flow(self):
        trip = self.create()
        url = f"/trips/{trip['id']}"
        self.assertEqual(self.client.get(url, headers=self.headers[0]).json()["id"], trip["id"])
        update = self.client.patch(url, json={"name": "Updated", "description": "New notes"}, headers=self.headers[0])
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["name"], "Updated")
        self.assertEqual(update.json()["destination"], self.payload["destination"])
        self.assertEqual(self.client.get(url, headers=self.headers[0]).json()["description"], "New notes")
        response = self.client.delete(url, headers=self.headers[0])
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get(url, headers=self.headers[0]).status_code, 404)
        self.assertEqual(self.client.get("/trips", headers=self.headers[0]).json(), [])

    def test_list_only_contains_members_trips_and_orders_newest_first(self):
        first = self.create()
        second = self.create(name="Second trip")
        other = self.create(user=1, name="Other user's trip")
        self.add_member(other["id"], user=0)
        rows = self.client.get("/trips", headers=self.headers[0]).json()
        self.assertEqual([row["id"] for row in rows], [other["id"], second["id"], first["id"]])
        self.assertEqual(self.client.get("/trips", headers=self.headers[2]).json(), [])

    def test_outsider_cannot_read_update_delete_or_list_trip(self):
        trip = self.create()
        url = f"/trips/{trip['id']}"
        for method, kwargs in [("get", {}), ("patch", {"json": {"name": "Intrusion"}}), ("delete", {})]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, headers=self.headers[1], **kwargs)
                self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/trips", headers=self.headers[1]).json(), [])
        self.assertEqual(self.client.get(url, headers=self.headers[0]).json()["name"], self.payload["name"])

    def test_member_can_read_but_not_edit_or_delete(self):
        trip = self.create()
        self.add_member(trip["id"])
        url = f"/trips/{trip['id']}"
        self.assertEqual(self.client.get(url, headers=self.headers[1]).status_code, 200)
        self.assertEqual(len(self.client.get("/trips", headers=self.headers[1]).json()), 1)
        self.assertEqual(self.client.patch(url, json={"name": "Denied"}, headers=self.headers[1]).status_code, 403)
        self.assertEqual(self.client.delete(url, headers=self.headers[1]).status_code, 403)

    def test_removed_member_immediately_loses_access(self):
        trip = self.create()
        self.add_member(trip["id"])
        with Session(self.engine) as db:
            db.delete(db.get(TripMember, (trip["id"], self.ids[1])))
            db.commit()
        self.assertEqual(self.client.get(f"/trips/{trip['id']}", headers=self.headers[1]).status_code, 404)
        self.assertEqual(self.client.get("/trips", headers=self.headers[1]).json(), [])

    def test_all_routes_require_authentication(self):
        for method, path, kwargs in [
            ("get", "/trips", {}),
            ("post", "/trips", {"json": self.payload}),
            ("get", "/trips/1", {}),
            ("patch", "/trips/1", {"json": {"name": "Denied"}}),
            ("delete", "/trips/1", {}),
        ]:
            with self.subTest(method=method, path=path):
                self.assertEqual(getattr(self.client, method)(path, **kwargs).status_code, 401)

    def test_creation_rejects_owner_id_and_unknown_fields(self):
        for changes in [{"owner_id": self.ids[1]}, {"members": [self.ids[1]]}]:
            response = self.client.post("/trips", json=self.payload | changes, headers=self.headers[0])
            self.assertEqual(response.status_code, 422)

    def test_create_validates_required_fields_lengths_and_dates(self):
        cases = [
            {"name": "  "}, {"name": "x" * 101},
            {"destination": "  "}, {"destination": "x" * 201},
            {"description": "x" * 2001}, {"start_date": "invalid"},
            {"end_date": "2027-02-02"}, {"end_date": "2027-02-30"},
            {"start_date": None}, {"end_date": None},
        ]
        for changes in cases:
            with self.subTest(fields=list(changes)):
                response = self.client.post("/trips", json=self.payload | changes, headers=self.headers[0])
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.post("/trips", json={}, headers=self.headers[0]).status_code, 422)

    def test_same_day_trip_is_valid_and_whitespace_is_normalized(self):
        trip = self.create(name="  Weekend  ", destination="  Taipei  ", end_date=self.payload["start_date"], description="  ")
        self.assertEqual(trip["name"], "Weekend")
        self.assertEqual(trip["destination"], "Taipei")
        self.assertIsNone(trip["description"])

    def test_patch_merges_dates_with_existing_values(self):
        trip = self.create()
        url = f"/trips/{trip['id']}"
        for changes in [{"start_date": "2027-02-11"}, {"end_date": "2027-02-02"}]:
            self.assertEqual(self.client.patch(url, json=changes, headers=self.headers[0]).status_code, 422)
        response = self.client.patch(url, json={"start_date": "2028-01-01", "end_date": "2028-01-02"}, headers=self.headers[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["start_date"], "2028-01-01")

    def test_patch_rejects_empty_null_invalid_and_immutable_fields(self):
        trip = self.create()
        url = f"/trips/{trip['id']}"
        for changes in [{}, {"name": None}, {"destination": None}, {"start_date": None}, {"end_date": None}, {"name": " "}, {"name": "x" * 101}, {"owner_id": self.ids[1]}, {"id": 100}]:
            with self.subTest(fields=list(changes)):
                self.assertEqual(self.client.patch(url, json=changes, headers=self.headers[0]).status_code, 422)

    def test_description_can_be_cleared(self):
        trip = self.create()
        response = self.client.patch(f"/trips/{trip['id']}", json={"description": None}, headers=self.headers[0])
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["description"])

    def test_delete_cascades_membership_and_preserves_other_trips_and_users(self):
        trip = self.create()
        other = self.create(name="Keep this")
        self.add_member(trip["id"])
        self.assertEqual(self.client.delete(f"/trips/{trip['id']}", headers=self.headers[0]).status_code, 204)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(TripMember).where(TripMember.trip_id == trip["id"])), 0)
            self.assertIsNotNone(db.get(Trip, other["id"]))
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 3)

    def test_database_rejects_duplicate_membership(self):
        trip = self.create()
        with Session(self.engine) as db:
            db.add(TripMember(trip_id=trip["id"], user_id=self.ids[0]))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_database_also_enforces_date_range(self):
        from datetime import date
        with Session(self.engine) as db:
            db.add(Trip(name="Invalid", destination="Taipei", start_date=date(2027, 2, 10), end_date=date(2027, 2, 1), owner_id=self.ids[0]))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_failed_membership_insert_rolls_back_entire_trip(self):
        def fail_membership(_mapper, _connection, _target):
            raise IntegrityError("simulated membership failure", {}, Exception("test"))

        event.listen(TripMember, "before_insert", fail_membership)
        try:
            response = self.client.post("/trips", json=self.payload, headers=self.headers[0])
            self.assertEqual(response.status_code, 500)
        finally:
            event.remove(TripMember, "before_insert", fail_membership)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Trip)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(TripMember)), 0)

    def test_invalid_ids_and_missing_trips(self):
        for value in ["0", "-1", "2147483648", "not-a-number"]:
            self.assertEqual(self.client.get(f"/trips/{value}", headers=self.headers[0]).status_code, 422)
        self.assertEqual(self.client.get("/trips/999", headers=self.headers[0]).status_code, 404)

    def test_personal_trip_responses_are_not_cached(self):
        trip = self.create()
        for response in [
            self.client.get("/trips", headers=self.headers[0]),
            self.client.get(f"/trips/{trip['id']}", headers=self.headers[0]),
            self.client.patch(f"/trips/{trip['id']}", json={"description": "Updated"}, headers=self.headers[0]),
        ]:
            self.assertEqual(response.headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
