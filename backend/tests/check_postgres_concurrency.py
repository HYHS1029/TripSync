"""Verify row-lock behavior in a disposable PostgreSQL schema, then remove it.

Run manually from backend/: python tests/check_postgres_concurrency.py
Uses the configured database, but all application tables/data are isolated by schema.
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import sys
from threading import Barrier, Event
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["JWT_SECRET_KEY"] = "tripsync-postgres-check-only-secret-key-123456789"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.database import Base, DATABASE_URL, get_db
from app.main import app
from app.models.invitation import TripInvitation
from app.models.trip import Trip, TripMember
from app.models.user import User


def main():
    if not DATABASE_URL.startswith("postgresql"):
        raise RuntimeError("This check requires PostgreSQL")
    schema = "tripsync_check_" + uuid4().hex
    assert re.fullmatch(r"tripsync_check_[a-f0-9]{32}", schema)
    engine = create_engine(DATABASE_URL, hide_parameters=True,
                           connect_args={"options": "-c lock_timeout=5000 -c statement_timeout=10000"})
    isolated = engine.execution_options(schema_translate_map={None: schema})
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        Base.metadata.create_all(isolated)
        with Session(isolated) as db:
            digest = hash_password("postgres-check-only-password")
            users = [User(email=f"pg{i}@example.com", username=f"pg{i}", password_hash=digest) for i in range(3)]
            db.add_all(users)
            db.commit()
            ids = [user.id for user in users]
        headers = [{"Authorization": f"Bearer {create_access_token(user_id)}"} for user_id in ids]

        def database():
            with Session(isolated) as db:
                yield db

        app.dependency_overrides[get_db] = database

        def request(method, path, user=0, **kwargs):
            with TestClient(app) as client:
                return client.request(method, path, headers=headers[user], **kwargs)

        def trip():
            response = request("POST", "/trips", json={"name": "Concurrency check", "destination": "Test", "start_date": "2027-02-03", "end_date": "2027-02-10"})
            assert response.status_code == 201
            return response.json()["id"]

        def invite(trip_id):
            response = request("POST", f"/trips/{trip_id}/invitations")
            assert response.status_code == 201
            return response.json()["token"]

        def parallel(functions):
            gate = Barrier(len(functions))
            def run(function):
                gate.wait(timeout=10)
                return function()
            with ThreadPoolExecutor(max_workers=len(functions)) as pool:
                futures = [pool.submit(run, function) for function in functions]
                return [future.result(timeout=20) for future in futures]

        trip_id = trip()
        token = invite(trip_id)
        responses = parallel([
            lambda: request("POST", "/invitations/accept", user=1, json={"token": token}),
            lambda: request("POST", "/invitations/accept", user=2, json={"token": token}),
        ])
        assert sorted(response.status_code for response in responses) == [200, 404]
        with Session(isolated) as db:
            assert db.scalar(select(func.count()).select_from(TripMember).where(TripMember.trip_id == trip_id)) == 2
        print("PASS: concurrent claims admit exactly one new member")

        trip_id = trip()
        token = invite(trip_id)
        responses = parallel([lambda: request("POST", "/invitations/accept", user=1, json={"token": token}) for _ in range(2)])
        assert [response.status_code for response in responses] == [200, 200]
        with Session(isolated) as db:
            assert db.scalar(select(func.count()).select_from(TripMember).where(TripMember.trip_id == trip_id)) == 2
        print("PASS: concurrent retries by the same user remain idempotent")

        waiting = Event()
        def observe(_connection, _cursor, statement, _params, _context, _many):
            if "FOR UPDATE" in statement:
                waiting.set()

        with Session(isolated) as owner_db:
            owner_db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update())
            event.listen(engine, "before_cursor_execute", observe)
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(request, "POST", f"/trips/{trip_id}/activities", user=1,
                                         json={"title": "Must be rejected", "activity_date": "2027-02-04"})
                    assert waiting.wait(timeout=10), "Activity request did not reach the trip lock"
                    owner_db.delete(owner_db.get(TripMember, (trip_id, ids[1])))
                    owner_db.commit()
                    assert future.result(timeout=20).status_code == 404
            finally:
                event.remove(engine, "before_cursor_execute", observe)
        print("PASS: a waiting writer rechecks membership after concurrent removal")

        trip_id = trip()
        for _ in range(9):
            invite(trip_id)
        responses = parallel([lambda: request("POST", f"/trips/{trip_id}/invitations") for _ in range(2)])
        assert sorted(response.status_code for response in responses) == [201, 429]
        with Session(isolated) as db:
            assert db.scalar(select(func.count()).select_from(TripInvitation).where(TripInvitation.trip_id == trip_id)) == 10
        print("PASS: concurrent invitation creation respects the database-backed limit")

        trip_id = trip()
        token = invite(trip_id)
        assert request("POST", "/invitations/accept", user=1, json={"token": token}).status_code == 200
        expense = {"title": "Shared hotel", "expense_date": "2027-02-03", "amount_minor": 10000,
                   "payer_id": ids[0], "participant_ids": ids[:2]}
        assert request("POST", f"/trips/{trip_id}/expenses", json=expense).status_code == 201
        repayment = {"sender_id": ids[1], "recipient_id": ids[0], "amount_minor": 5000, "settled_on": "2027-02-04"}
        responses = parallel([lambda: request("POST", f"/trips/{trip_id}/settlements", json=repayment) for _ in range(2)])
        assert sorted(response.status_code for response in responses) == [201, 409]
        ledger = request("GET", f"/trips/{trip_id}/ledger").json()
        assert len(ledger["settlements"]) == 1
        assert all(person["balance_minor"] == 0 for person in ledger["balances"])
        print("PASS: concurrent full repayments cannot over-settle the same balance")

        waiting.clear()
        with Session(isolated) as owner_db:
            owner_db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update())
            event.listen(engine, "before_cursor_execute", observe)
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(request, "POST", f"/trips/{trip_id}/expenses", user=1, json=expense)
                    assert waiting.wait(timeout=10)
                    owner_db.delete(owner_db.get(TripMember, (trip_id, ids[1])))
                    owner_db.commit()
                    assert future.result(timeout=20).status_code == 404
            finally:
                event.remove(engine, "before_cursor_execute", observe)
        print("PASS: waiting expense writers recheck membership after removal")
    finally:
        app.dependency_overrides.clear()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
        print("PASS: disposable PostgreSQL schema removed")


if __name__ == "__main__":
    main()
