from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from test_trips import TripTestCase

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_invitation_token
from app.models.invitation import TripInvitation
from app.models.trip import TripMember


class MemberTests(TripTestCase):
    def setUp(self):
        super().setUp()
        self.trip = self.create()
        self.url = f"/trips/{self.trip['id']}"

    def invite(self):
        response = self.client.post(self.url + "/invitations", headers=self.headers[0])
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def accept(self, token, user=1):
        return self.client.post("/invitations/accept", json={"token": token}, headers=self.headers[user])

    def test_all_member_and_invitation_endpoints_require_login(self):
        invitation = self.invite()
        cases = [
            ("get", self.url + "/members", {}),
            ("delete", self.url + "/members/me", {}),
            ("delete", self.url + f"/members/{self.ids[1]}", {}),
            ("get", self.url + "/invitations", {}),
            ("post", self.url + "/invitations", {}),
            ("delete", self.url + f"/invitations/{invitation['id']}", {}),
            ("post", "/invitations/accept", {"json": {"token": invitation["token"]}}),
        ]
        for method, url, kwargs in cases:
            with self.subTest(method=method, url=url):
                self.assertEqual(getattr(self.client, method)(url, **kwargs).status_code, 401)

    def test_owner_only_controls_and_outsider_privacy(self):
        self.add_member(self.trip["id"])
        invitation = self.invite()
        for user, expected in [(1, 403), (2, 404)]:
            for method, suffix in [("get", "/invitations"), ("post", "/invitations"),
                                   ("delete", f"/invitations/{invitation['id']}"),
                                   ("delete", f"/members/{self.ids[1]}")]:
                with self.subTest(user=user, method=method):
                    self.assertEqual(getattr(self.client, method)(self.url + suffix, headers=self.headers[user]).status_code, expected)
        self.assertEqual(self.client.get(self.url + "/members", headers=self.headers[2]).status_code, 404)

    def test_members_expose_only_minimal_fields_and_owner_first(self):
        self.add_member(self.trip["id"])
        response = self.client.get(self.url + "/members", headers=self.headers[1])
        self.assertEqual(response.headers["cache-control"], "no-store")
        rows = response.json()
        self.assertEqual([row["is_owner"] for row in rows], [True, False])
        self.assertEqual(set(rows[0]), {"user_id", "username", "joined_at", "is_owner"})
        self.assertNotIn("email", response.text)

    def test_token_is_random_hashed_and_returned_only_on_creation(self):
        invitation = self.invite()
        second = self.invite()
        self.assertRegex(invitation["token"], r"^[A-Za-z0-9_-]{43}$")
        self.assertNotEqual(invitation["token"], second["token"])
        with Session(self.engine) as db:
            row = db.get(TripInvitation, invitation["id"])
            self.assertEqual(row.token_hash, hash_invitation_token(invitation["token"]))
            self.assertNotEqual(row.token_hash, invitation["token"])
            self.assertLess(abs((row.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() - 7 * 86400), 10)
        listing = self.client.get(self.url + "/invitations", headers=self.headers[0])
        self.assertEqual(listing.headers["cache-control"], "no-store")
        self.assertNotIn(invitation["token"], listing.text)
        self.assertNotIn("token_hash", listing.text)
        self.assertNotIn("token", listing.json()[0])

    def test_acceptance_is_single_use_and_same_member_retry_is_idempotent(self):
        invitation = self.invite()
        for _ in range(2):
            response = self.accept(invitation["token"])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["id"], self.trip["id"])
        self.assertEqual(self.accept(invitation["token"], user=2).status_code, 404)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(TripMember).where(TripMember.trip_id == self.trip["id"])), 2)
            self.assertEqual(db.get(TripInvitation, invitation["id"]).accepted_by, self.ids[1])
        self.assertEqual(self.client.get(self.url, headers=self.headers[1]).status_code, 200)

    def test_existing_member_does_not_consume_a_new_invitation(self):
        invitation = self.invite()
        self.assertEqual(self.accept(invitation["token"], user=0).status_code, 200)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(TripInvitation, invitation["id"]).accepted_at)
        self.assertEqual(self.accept(invitation["token"]).status_code, 200)

    def test_expired_revoked_and_unknown_links_have_same_error(self):
        expired = self.invite()
        revoked = self.invite()
        with Session(self.engine) as db:
            db.get(TripInvitation, expired["id"]).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.client.delete(self.url + f"/invitations/{revoked['id']}", headers=self.headers[0]).status_code, 204)
        results = [self.accept(token) for token in [expired["token"], revoked["token"], "a" * 43]]
        for response in results:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), results[0].json())
            self.assertNotIn(self.trip["name"], response.text)

    def test_owner_cannot_leave_or_be_removed(self):
        for suffix in ["/members/me", f"/members/{self.ids[0]}"]:
            self.assertEqual(self.client.delete(self.url + suffix, headers=self.headers[0]).status_code, 409)
        self.assertEqual(self.client.get(self.url, headers=self.headers[0]).status_code, 200)

    def test_removal_revokes_access_and_used_link_cannot_rejoin(self):
        invitation = self.invite()
        self.assertEqual(self.accept(invitation["token"]).status_code, 200)
        response = self.client.delete(self.url + f"/members/{self.ids[1]}", headers=self.headers[0])
        self.assertEqual(response.status_code, 204)
        for suffix in ["", "/members", "/activities"]:
            self.assertEqual(self.client.get(self.url + suffix, headers=self.headers[1]).status_code, 404)
        self.assertEqual(self.accept(invitation["token"]).status_code, 404)
        self.assertEqual(self.client.get("/trips", headers=self.headers[1]).json(), [])

    def test_member_can_leave_without_deleting_the_trip(self):
        invitation = self.invite()
        self.accept(invitation["token"])
        self.assertEqual(self.client.delete(self.url + "/members/me", headers=self.headers[1]).status_code, 204)
        self.assertEqual(self.client.get(self.url, headers=self.headers[0]).status_code, 200)
        self.assertEqual(self.accept(invitation["token"]).status_code, 404)

    def test_invitation_ids_are_scoped_to_trip(self):
        invitation = self.invite()
        other = self.create(name="Another trip")
        self.assertEqual(self.client.delete(f"/trips/{other['id']}/invitations/{invitation['id']}", headers=self.headers[0]).status_code, 404)
        self.assertEqual(self.accept(invitation["token"]).status_code, 200)

    def test_creation_limit_includes_revoked_invitations(self):
        for _ in range(10):
            invitation = self.invite()
            self.client.delete(self.url + f"/invitations/{invitation['id']}", headers=self.headers[0])
        response = self.client.post(self.url + "/invitations", headers=self.headers[0])
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "3600")

    def test_member_cap_does_not_consume_failed_invitation(self):
        first, second = self.invite(), self.invite()
        self.accept(first["token"])
        with patch("app.api.members.MAX_MEMBERS", 2):
            self.assertEqual(self.accept(second["token"], user=2).status_code, 409)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(TripInvitation, second["id"]).accepted_at)
        self.assertEqual(self.accept(second["token"], user=2).status_code, 200)

    def test_acceptance_rolls_back_both_membership_and_token_on_failure(self):
        invitation = self.invite()
        with patch("sqlalchemy.orm.Session.commit", side_effect=SQLAlchemyError("forced")):
            self.assertEqual(self.accept(invitation["token"]).status_code, 500)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(TripMember, (self.trip["id"], self.ids[1])))
            self.assertIsNone(db.get(TripInvitation, invitation["id"]).accepted_at)
        self.assertEqual(self.accept(invitation["token"]).status_code, 200)

    def test_validation_does_not_echo_credentials(self):
        for token in ["secret-invalid-token", "x" * 5000, self.headers[0]["Authorization"].split()[1]]:
            response = self.accept(token)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(token, response.text)
            self.assertNotIn('"input"', response.text)
        response = self.client.post("/auth/login", json={"email": "invalid@", "password": "private-password"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-password", response.text)

    def test_acceptance_consistency_is_enforced_by_database(self):
        invitation = self.invite()
        with Session(self.engine) as db:
            db.get(TripInvitation, invitation["id"]).accepted_by = self.ids[1]
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_delete_trip_cascades_invitations(self):
        self.invite()
        self.assertEqual(self.client.delete(self.url, headers=self.headers[0]).status_code, 204)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(TripInvitation)), 0)
