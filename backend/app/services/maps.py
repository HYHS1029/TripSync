import httpx
from fastapi import HTTPException

from app.core.config import get_settings


def maps_enabled() -> bool:
    key = get_settings().google_maps_api_key
    return bool(key and key.get_secret_value().strip())


async def google_request(method: str, url: str, fields: str, payload=None):
    if not maps_enabled():
        raise HTTPException(status_code=503, detail="Google Maps is not configured")
    headers = {"X-Goog-Api-Key": get_settings().google_maps_api_key.get_secret_value(),
               "X-Goog-FieldMask": fields}
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.request(method, url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        # Provider bodies and URLs may contain sensitive information; never expose them.
        raise HTTPException(status_code=502, detail="Google Maps is temporarily unavailable") from None


def place_result(place):
    location = place.get("location", {})
    return {"place_id": place["id"], "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "lat": location.get("latitude"), "lng": location.get("longitude")}


async def search_places(query: str):
    result = await google_request("POST", "https://places.googleapis.com/v1/places:searchText",
                                  "places.id,places.displayName,places.formattedAddress,places.location",
                                  {"textQuery": query, "languageCode": "zh-TW", "pageSize": 5})
    return [place_result(place) for place in result.get("places", [])]


async def place_details(place_id: str):
    result = await google_request("GET", f"https://places.googleapis.com/v1/places/{place_id}?languageCode=zh-TW",
                                  "id,displayName,formattedAddress,location")
    return place_result(result)
