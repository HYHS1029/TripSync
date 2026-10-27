from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from test_trips import TripTestCase


class MapsTests(TripTestCase):
    def setUp(self):
        super().setUp()
        day = datetime.now(timezone.utc).date() + timedelta(days=1)
        self.day = day.isoformat()
        self.end = (day + timedelta(days=3)).isoformat()
        self.trip = self.create(start_date=self.day, end_date=self.end, timezone="Asia/Tokyo")
        self.base = f"/trips/{self.trip['id']}"
        self.origin = self.add_activity("Hotel", category="lodging", stay_until=self.end, start_time="08:00", end_time="09:00")
        self.destination = self.add_activity("Station", category="station", start_time="09:10")

    def add_activity(self, title, **changes):
        payload = {"title": title, "activity_date": self.day, "place_id": title.replace(" ", "_")}
        response = self.client.post(self.base + "/activities", json=payload | changes, headers=self.headers[0])
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def route(self, **changes):
        return self.client.post(self.base + "/routes", json={"origin_id": self.origin["id"], "destination_id": self.destination["id"],
            "day": self.day, "mode": "TRANSIT"} | changes, headers=self.headers[0])

    def test_route_uses_trip_local_time_and_returns_conflict_and_geometry(self):
        response_data = {"routes": [{"duration": "1200s", "distanceMeters": 1800, "polyline": {"encodedPolyline": "abc"},
            "legs": [{"steps": [{"transitDetails": {"transitLine": {"nameShort": "JR"}, "stopDetails": {
                "departureStop": {"name": "A"}, "arrivalStop": {"name": "B"}}}}]}]}]}
        with patch("app.api.maps.google_request", new=AsyncMock(return_value=response_data)) as request:
            response = self.route()
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["minutes"], 20)
            self.assertTrue(response.json()["time_conflict"])
            self.assertEqual(response.json()["polyline"], "abc")
            self.assertEqual(response.json()["steps"][0]["line"], "JR")
            self.assertEqual(request.call_args.args[3]["departureTime"], self.day + "T00:00:00Z")

    def test_far_future_transit_does_not_request_fake_schedule(self):
        far = (datetime.now(timezone.utc).date() + timedelta(days=200)).isoformat()
        trip = self.create(start_date=far, end_date=far)
        base = f"/trips/{trip['id']}"
        ids = [self.client.post(base + "/activities", json={"title": str(i), "activity_date": far, "place_id": f"place{i}"}, headers=self.headers[0]).json()["id"] for i in range(2)]
        with patch("app.api.maps.google_request", new=AsyncMock()) as request:
            response = self.client.post(base + "/routes", json={"origin_id": ids[0], "destination_id": ids[1], "day": far,
                "departure_time": "09:00"}, headers=self.headers[0])
            self.assertEqual(response.json()["status"], "date_unavailable")
            request.assert_not_awaited()

    def test_empty_routes_and_missing_places_have_clear_results(self):
        with patch("app.api.maps.google_request", new=AsyncMock(return_value={"routes": []})):
            self.assertEqual(self.route().json()["status"], "no_route")
        unlinked = self.add_activity("Unlinked", place_id=None)
        self.assertEqual(self.route(destination_id=unlinked["id"]).status_code, 422)
        self.assertEqual(self.route(mode="FLY").status_code, 422)
        self.assertEqual(self.route(departure_time="09:00+08:00").status_code, 422)

    def test_activity_ids_are_scoped_and_require_membership(self):
        other = self.create(start_date=self.day, end_date=self.end)
        alien = self.client.post(f"/trips/{other['id']}/activities", json={"title": "Other", "activity_date": self.day, "place_id": "other"}, headers=self.headers[0]).json()
        self.assertEqual(self.route(destination_id=alien["id"]).status_code, 404)
        for path in ("/maps/status", "/map-points?day=" + self.day, "/places/search?q=Tokyo"):
            self.assertEqual(self.client.get(self.base + path, headers=self.headers[1]).status_code, 404)

    def test_map_points_include_inherited_lodging_and_isolate_partial_failures(self):
        next_day = (datetime.fromisoformat(self.day) + timedelta(days=1)).date().isoformat()
        async def details(place_id):
            return {"place_id": place_id, "name": "Google name", "address": "Google address", "lat": 35.0, "lng": 139.0}
        with patch("app.api.maps.maps_enabled", return_value=True), patch("app.api.maps.place_details", side_effect=details):
            response = self.client.get(self.base + "/map-points", params={"day": next_day}, headers=self.headers[0])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([point["activity_id"] for point in response.json()["points"]], [self.origin["id"]])
            all_points = self.client.get(self.base + "/map-points", params={"day": next_day, "all_days": True}, headers=self.headers[0]).json()
            self.assertEqual(len(all_points["points"]), 2)

    def test_disabled_maps_preserve_activity_operations(self):
        with patch("app.api.maps.maps_enabled", return_value=False):
            self.assertFalse(self.client.get(self.base + "/maps/status", headers=self.headers[0]).json()["enabled"])
            self.assertEqual(self.client.get(self.base + "/map-points", params={"day": self.day}, headers=self.headers[0]).status_code, 503)
        self.add_activity("Still editable", place_id=None)

    def test_reorder_is_independent_of_time_and_checks_complete_day(self):
        url = self.base + "/activities/reorder"
        payload = {"activity_date": self.day, "activity_ids": [self.destination["id"], self.origin["id"]]}
        self.assertEqual(self.client.post(url, json=payload, headers=self.headers[0]).status_code, 204)
        rows = self.client.get(self.base + "/activities", headers=self.headers[0]).json()
        self.assertEqual([row["id"] for row in rows], payload["activity_ids"])
        self.add_activity("Append", start_time="01:00")
        rows = self.client.get(self.base + "/activities", headers=self.headers[0]).json()
        self.assertEqual(rows[-1]["title"], "Append")
        self.assertEqual(self.client.post(url, json=payload, headers=self.headers[0]).status_code, 409)

    def test_invalid_lodging_range_and_place_reference_are_rejected(self):
        for changes in ({"stay_until": "2099-01-01"}, {"category": "sight", "stay_until": self.end},
                        {"place_id": "../../secrets"}, {"position": -1}):
            response = self.client.post(self.base + "/activities", json={"title": "Bad", "activity_date": self.day} | changes, headers=self.headers[0])
            self.assertEqual(response.status_code, 422, response.text)

    def test_search_results_are_scoped_to_authenticated_trip(self):
        with patch("app.api.maps.search_places", new=AsyncMock(return_value=[{"place_id": "Tokyo", "name": "Tokyo Station"}])) as search:
            response = self.client.get(self.base + "/places/search?q=Tokyo", headers=self.headers[0])
            self.assertEqual(response.status_code, 200)
            search.assert_awaited_once_with("Tokyo")

    def test_failed_place_is_reported_without_hiding_other_points(self):
        async def details(place_id):
            if place_id == "Hotel":
                raise HTTPException(status_code=502, detail="Unavailable")
            return {"place_id": place_id, "name": "Station", "address": "Address", "lat": 35.0, "lng": 139.0}
        with patch("app.api.maps.maps_enabled", return_value=True), patch("app.api.maps.place_details", side_effect=details):
            response = self.client.get(self.base + "/map-points", params={"day": self.day}, headers=self.headers[0])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["unavailable_ids"], [self.origin["id"]])
            self.assertEqual(len(response.json()["points"]), 1)

    def test_nonexistent_local_time_is_rejected_before_provider_request(self):
        trip = self.create(start_date="2027-03-14", end_date="2027-03-14", timezone="America/New_York")
        base = f"/trips/{trip['id']}"
        ids = [self.client.post(base + "/activities", json={"title": str(i), "activity_date": "2027-03-14", "place_id": f"point{i}"}, headers=self.headers[0]).json()["id"] for i in range(2)]
        with patch("app.api.maps.google_request", new=AsyncMock()) as request:
            response = self.client.post(base + "/routes", json={"origin_id": ids[0], "destination_id": ids[1], "day": "2027-03-14", "mode": "WALK", "departure_time": "02:30"}, headers=self.headers[0])
            self.assertEqual(response.status_code, 422)
            request.assert_not_awaited()
