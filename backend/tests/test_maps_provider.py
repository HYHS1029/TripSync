import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from pydantic import SecretStr

from app.services.maps import google_request, place_details, search_places


class MapsProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_service_makes_no_network_request(self):
        with patch("app.services.maps.maps_enabled", return_value=False), patch("app.services.maps.httpx.AsyncClient") as client:
            with self.assertRaises(HTTPException) as result:
                await google_request("GET", "https://places.googleapis.com/v1/places/Test", "id")
            self.assertEqual(result.exception.status_code, 503)
            client.assert_not_called()

    async def test_provider_error_is_sanitized(self):
        response = httpx.Response(403, json={"error": "sensitive-provider-detail"}, request=httpx.Request("GET", "https://places.googleapis.com/"))
        client = AsyncMock()
        client.request.return_value = response
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        with patch("app.services.maps.maps_enabled", return_value=True), patch("app.services.maps.get_settings", return_value=SimpleNamespace(google_maps_api_key=SecretStr("test-key"))), patch("app.services.maps.httpx.AsyncClient", return_value=manager):
            with self.assertRaises(HTTPException) as result:
                await google_request("GET", "https://places.googleapis.com/", "id")
            self.assertEqual(result.exception.status_code, 502)
            self.assertNotIn("sensitive", result.exception.detail)
            self.assertNotIn("test-key", result.exception.detail)

    async def test_search_requests_bounded_fields_and_parses_transient_details(self):
        response = {"places": [{"id": "Place", "displayName": {"text": "Station"}, "formattedAddress": "Address", "location": {"latitude": 35, "longitude": 139}}]}
        with patch("app.services.maps.google_request", new=AsyncMock(return_value=response)) as request:
            results = await search_places("Tokyo Station")
            self.assertEqual(results[0]["place_id"], "Place")
            self.assertEqual(results[0]["lat"], 35)
            self.assertEqual(request.call_args.args[3]["pageSize"], 5)
            self.assertNotIn("*", request.call_args.args[2])

    async def test_details_use_saved_id_and_return_no_raw_provider_body(self):
        response = {"id": "Place", "displayName": {"text": "Station"}, "location": {"latitude": 35, "longitude": 139}, "unused": "not returned"}
        with patch("app.services.maps.google_request", new=AsyncMock(return_value=response)) as request:
            details = await place_details("Place")
            self.assertIn("/places/Place?", request.call_args.args[1])
            self.assertNotIn("unused", details)
