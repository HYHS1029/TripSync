import asyncio
import math
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.activities import activity_order, find_activity
from app.api.trips import CurrentUser, Database, TripId, get_member_trip
from app.schemas.maps import RouteInput
from app.models.activity import Activity
from app.services.maps import google_request, maps_enabled, place_details, search_places


router = APIRouter(prefix="/trips/{trip_id}", tags=["maps"])


def available(activity, day):
    return activity.activity_date == day or (activity.category == "lodging" and activity.stay_until is not None
                                             and activity.activity_date <= day <= activity.stay_until)


@router.get("/maps/status")
def maps_status(trip_id: TripId, db: Database, user: CurrentUser):
    get_member_trip(trip_id, user.id, db)
    return {"enabled": maps_enabled()}


@router.get("/places/search")
async def find_places(trip_id: TripId, q: Annotated[str, Query(min_length=2, max_length=200)],
                      db: Database, user: CurrentUser):
    get_member_trip(trip_id, user.id, db)
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Enter at least two characters")
    return await search_places(query)


@router.get("/map-points")
async def map_points(trip_id: TripId, day: date, db: Database, user: CurrentUser, all_days: bool = False):
    trip = get_member_trip(trip_id, user.id, db)
    if not trip.start_date <= day <= trip.end_date:
        raise HTTPException(status_code=422, detail="Day must be within trip dates")
    if not maps_enabled():
        raise HTTPException(status_code=503, detail="Google Maps is not configured")
    activities = db.scalars(select(Activity).where(Activity.trip_id == trip_id).order_by(*activity_order())).all()
    located = [item for item in activities if item.place_id and (all_days or available(item, day))]
    unique = list(dict.fromkeys(item.place_id for item in located))
    if len(unique) > 100:
        raise HTTPException(status_code=422, detail="Too many map places; select a single day")
    semaphore = asyncio.Semaphore(5)

    async def resolve(place_id):
        async with semaphore:
            try:
                return place_id, await place_details(place_id)
            except HTTPException:
                return place_id, None

    tasks = [asyncio.create_task(resolve(place_id)) for place_id in unique]
    details = {place_id: None for place_id in unique}
    if tasks:
        done, pending = await asyncio.wait(tasks, timeout=8)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        details.update(task.result() for task in done)
    return {"points": [dict(details[item.place_id], activity_id=item.id, category=item.category,
                            title=item.title, day=item.activity_date.isoformat()) for item in located
                       if details[item.place_id] and details[item.place_id]["lat"] is not None],
            "unavailable_ids": [item.id for item in located if not details[item.place_id]],
            "queried_at": datetime.now(timezone.utc).isoformat()}


@router.post("/routes")
async def compute_route(trip_id: TripId, payload: RouteInput, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db)
    origin = find_activity(trip_id, payload.origin_id, db)
    destination = find_activity(trip_id, payload.destination_id, db)
    if not trip.start_date <= payload.day <= trip.end_date or not all(available(item, payload.day) for item in (origin, destination)):
        raise HTTPException(status_code=422, detail="Activities must be available on the requested day")
    if not origin.place_id or not destination.place_id:
        raise HTTPException(status_code=422, detail="Select map places for both activities")
    local_time = payload.departure_time or (origin.end_time if origin.activity_date == payload.day else None)
    if local_time is None:
        raise HTTPException(status_code=422, detail="Choose a departure time")
    departure = datetime.combine(payload.day, local_time, tzinfo=ZoneInfo(trip.timezone)).astimezone(timezone.utc)
    if departure.astimezone(ZoneInfo(trip.timezone)).replace(tzinfo=None) != datetime.combine(payload.day, local_time):
        raise HTTPException(status_code=422, detail="Departure time does not exist due to daylight saving time")
    now = datetime.now(timezone.utc)
    if payload.mode == "TRANSIT" and not now - timedelta(days=7) <= departure <= now + timedelta(days=100):
        return {"status": "date_unavailable", "message": "班次日期超出查詢範圍，請於出發前再確認。"}
    body = {"origin": {"placeId": origin.place_id}, "destination": {"placeId": destination.place_id},
            "travelMode": payload.mode, "languageCode": "zh-TW", "units": "METRIC"}
    if payload.mode == "TRANSIT":
        body["departureTime"] = departure.isoformat().replace("+00:00", "Z")
    fields = "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
    if payload.mode == "TRANSIT":
        fields += ",routes.legs.steps.transitDetails"
    result = await google_request("POST", "https://routes.googleapis.com/directions/v2:computeRoutes", fields, body)
    routes = result.get("routes", [])
    if not routes:
        return {"status": "no_route", "message": "這個時間沒有可用路線，可更換交通方式或出發時間。"}
    route = routes[0]
    seconds = math.ceil(float(route["duration"].removesuffix("s")))
    arrival = departure + timedelta(seconds=seconds)
    next_start = (datetime.combine(payload.day, destination.start_time, tzinfo=ZoneInfo(trip.timezone))
                  if destination.start_time and destination.activity_date == payload.day else None)
    steps = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            transit = step.get("transitDetails")
            if transit:
                stops = transit.get("stopDetails", {})
                line = transit.get("transitLine", {})
                steps.append({"line": line.get("nameShort") or line.get("name", "大眾運輸"),
                              "from": stops.get("departureStop", {}).get("name", ""),
                              "to": stops.get("arrivalStop", {}).get("name", "")})
    return {"status": "ok", "minutes": math.ceil(seconds / 60), "distance_meters": route.get("distanceMeters", 0),
            "polyline": route.get("polyline", {}).get("encodedPolyline", ""), "steps": steps,
            "departure_at": departure.isoformat(), "arrival_at": arrival.isoformat(),
            "time_conflict": bool(next_start and arrival > next_start), "mode": payload.mode,
            "queried_at": now.isoformat(), "traffic_included": False}
