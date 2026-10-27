from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_trips import TripTestCase
from app.models.expense import Expense, ExpenseShare, Settlement


class ExpenseTests(TripTestCase):
    def setUp(self):
        super().setUp()
        self.trip = self.create()
        self.add_member(self.trip["id"])
        self.add_member(self.trip["id"], user=2)
        self.base = f"/trips/{self.trip['id']}"
        self.expense = {"title": "Hotel", "expense_date": "2027-01-01", "category": "lodging",
                        "amount_minor": 10000, "payer_id": self.ids[0], "participant_ids": self.ids, "split_mode": "equal"}

    def add_expense(self, user=0, **changes):
        response = self.client.post(self.base + "/expenses", json=self.expense | changes, headers=self.headers[user])
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def ledger(self, user=0):
        response = self.client.get(self.base + "/ledger", headers=self.headers[user])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        return response.json()

    def settle(self, amount=3333, **changes):
        return self.client.post(self.base + "/settlements", json={"sender_id": self.ids[1], "recipient_id": self.ids[0],
            "amount_minor": amount, "settled_on": "2027-02-05"} | changes, headers=self.headers[0])

    def test_equal_rounding_is_deterministic_and_balances_sum_to_zero(self):
        item = self.add_expense(participant_ids=list(reversed(self.ids)))
        self.assertEqual([share["amount_minor"] for share in item["shares"]], [3334, 3333, 3333])
        ledger = self.ledger()
        self.assertEqual(ledger["total_minor"], 10000)
        self.assertEqual(sum(person["balance_minor"] for person in ledger["balances"]), 0)
        self.assertEqual([person["balance_minor"] for person in ledger["balances"]], [6666, -3333, -3333])
        self.assertEqual(sum(row["amount_minor"] for row in ledger["suggestions"]), 6666)

    def test_payer_can_be_excluded_and_custom_shares_allow_zero(self):
        item = self.add_expense(split_mode="custom", participant_ids=self.ids[1:], custom_shares=[
            {"user_id": self.ids[1], "amount_minor": 0}, {"user_id": self.ids[2], "amount_minor": 10000}])
        self.assertEqual(len(item["shares"]), 2)
        self.assertEqual([p["balance_minor"] for p in self.ledger()["balances"]], [10000, 0, -10000])

    def test_invalid_splits_and_float_money_are_rejected(self):
        cases = [{"amount_minor": 0}, {"amount_minor": 10.5}, {"amount_minor": True}, {"amount_minor": 10**12 + 1},
                 {"participant_ids": []}, {"participant_ids": [self.ids[0]] * 2}, {"participant_ids": [999]},
                 {"payer_id": 999}, {"split_mode": "custom", "custom_shares": []},
                 {"split_mode": "equal", "custom_shares": [{"user_id": self.ids[0], "amount_minor": 1}]},
                 {"currency": "JPY"}, {"activity_id": 999}]
        for changes in cases:
            with self.subTest(changes=changes):
                response = self.client.post(self.base + "/expenses", json=self.expense | changes, headers=self.headers[0])
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.ledger()["total_minor"], 0)

    def test_custom_total_and_parties_must_match(self):
        for shares in [[{"user_id": user_id, "amount_minor": 1} for user_id in self.ids],
                       [{"user_id": self.ids[0], "amount_minor": 10000}] * 3]:
            response = self.client.post(self.base + "/expenses", json=self.expense | {"split_mode": "custom", "custom_shares": shares}, headers=self.headers[0])
            self.assertEqual(response.status_code, 422)

    def test_partial_repayment_and_revocation_update_balances(self):
        self.add_expense()
        response = self.settle(1000)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual([p["balance_minor"] for p in self.ledger()["balances"]], [5666, -2333, -3333])
        self.assertEqual(self.settle(2334).status_code, 409)
        self.assertEqual(self.settle(2333).status_code, 201)
        self.assertEqual(self.settle(1).status_code, 409)
        self.assertEqual(self.client.delete(self.base + f"/settlements/{response.json()['id']}", headers=self.headers[0]).status_code, 204)
        self.assertEqual(self.ledger()["balances"][1]["balance_minor"], -1000)

    def test_repayments_cannot_reverse_parties_or_create_money(self):
        self.add_expense()
        self.assertEqual(self.settle(1, sender_id=self.ids[0], recipient_id=self.ids[1]).status_code, 409)
        self.assertEqual(self.settle(1, recipient_id=self.ids[1]).status_code, 422)
        self.assertEqual(self.settle(0).status_code, 422)

    def test_expense_edit_and_delete_recalculate_without_deleting_repayments(self):
        item = self.add_expense()
        self.assertEqual(self.settle(1000).status_code, 201)
        response = self.client.put(self.base + f"/expenses/{item['id']}", json=self.expense | {"amount_minor": 3000}, headers=self.headers[0])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.ledger()["total_minor"], 3000)
        self.assertEqual(self.client.delete(self.base + f"/expenses/{item['id']}", headers=self.headers[0]).status_code, 204)
        ledger = self.ledger()
        self.assertEqual(ledger["total_minor"], 0)
        self.assertEqual(len(ledger["settlements"]), 1)
        self.assertEqual(sum(p["balance_minor"] for p in ledger["balances"]), 0)

    def test_creator_and_owner_can_edit_but_other_members_cannot(self):
        item = self.add_expense(user=1)
        url = self.base + f"/expenses/{item['id']}"
        self.assertEqual(self.client.put(url, json=self.expense, headers=self.headers[2]).status_code, 403)
        self.assertEqual(self.client.delete(url, headers=self.headers[2]).status_code, 403)
        self.assertEqual(self.client.put(url, json=self.expense, headers=self.headers[1]).status_code, 200)
        self.assertEqual(self.client.delete(url, headers=self.headers[0]).status_code, 204)

    def test_private_trip_and_entry_ids_are_scoped(self):
        item = self.add_expense()
        other = self.create(user=2)
        base = f"/trips/{other['id']}"
        self.assertEqual(self.client.get(base + "/ledger", headers=self.headers[0]).status_code, 404)
        self.assertEqual(self.client.put(base + f"/expenses/{item['id']}", json=self.expense, headers=self.headers[2]).status_code, 404)
        self.assertEqual(self.client.get(self.base + "/ledger").status_code, 401)

    def test_departed_members_keep_history_and_can_finish_repayments(self):
        item = self.add_expense()
        self.assertEqual(self.client.delete(self.base + "/members/me", headers=self.headers[1]).status_code, 204)
        self.assertEqual(self.client.get(self.base + "/ledger", headers=self.headers[1]).status_code, 404)
        self.assertFalse(self.ledger()["balances"][1]["active"])
        self.assertEqual(self.settle().status_code, 201)
        response = self.client.put(self.base + f"/expenses/{item['id']}", json=self.expense | {"amount_minor": 9000}, headers=self.headers[0])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.post(self.base + "/expenses", json=self.expense, headers=self.headers[0]).status_code, 422)

    def test_activity_links_and_trip_currency_guard(self):
        activity = self.client.post(self.base + "/activities", json={"title": "Hotel", "activity_date": "2027-02-03"}, headers=self.headers[0]).json()
        item = self.add_expense(activity_id=activity["id"])
        self.assertEqual(self.client.patch(self.base, json={"currency": "JPY"}, headers=self.headers[0]).status_code, 409)
        self.client.delete(self.base + f"/activities/{activity['id']}", headers=self.headers[0])
        self.assertIsNone(self.ledger()["expenses"][0]["activity_id"])
        self.assertEqual(self.ledger()["expenses"][0]["id"], item["id"])

    def test_trip_deletion_cascades_ledger(self):
        self.add_expense()
        self.settle()
        self.client.delete(self.base, headers=self.headers[0])
        with Session(self.engine) as db:
            for model in (Expense, ExpenseShare, Settlement):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0)

    def test_entry_limit(self):
        with patch("app.api.expenses.MAX_ENTRIES", 1):
            self.add_expense()
            self.assertEqual(self.client.post(self.base + "/expenses", json=self.expense, headers=self.headers[0]).status_code, 409)

    def test_zero_decimal_currency_and_timezone_validation(self):
        trip = self.create(currency="JPY", timezone="Asia/Tokyo")
        self.assertEqual(trip["currency"], "JPY")
        self.assertEqual(self.client.get(f"/trips/{trip['id']}/ledger", headers=self.headers[0]).json()["minor_digits"], 0)
        self.assertEqual(self.client.patch(self.base, json={"timezone": "Not/A_Zone"}, headers=self.headers[0]).status_code, 422)
        self.assertEqual(self.client.patch(self.base, json={"currency": "XXX"}, headers=self.headers[0]).status_code, 422)
