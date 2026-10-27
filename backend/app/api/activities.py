from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select

from app.api.trips import CurrentUser, Database, TripId, get_member_trip
from app.database import commit_transaction
from app.models.activity import Activity
from app.models.trip import Trip
from app.schemas.activity import ActivityInput, ActivityOrder, ActivityResponse


router = APIRouter(prefix="/trips/{trip_id}/activities", tags=["activities"])
MAX_ACTIVITIES = 500


def validate_day(payload: ActivityInput, trip: Trip) -> None:
    if not trip.start_date <= payload.activity_date <= trip.end_date:
        raise HTTPException(status_code=422, detail=[{
            "loc": ["body", "activity_date"], "msg": "Activity must be within trip dates", "type": "value_error"
        }])
    if payload.stay_until and payload.stay_until > trip.end_date:
        raise HTTPException(status_code=422, detail="Checkout must be within trip dates")


def activity_order():
    return (Activity.activity_date, func.coalesce(Activity.position, 0), Activity.start_time.asc().nullslast(), Activity.id)


def next_position(trip_id: int, day, db: Database):
    last = db.scalar(select(func.max(Activity.position)).where(
        Activity.trip_id == trip_id, Activity.activity_date == day))
    return last + 1 if last is not None else None


def find_activity(trip_id: int, activity_id: int, db: Database) -> Activity:
    activity = db.scalar(select(Activity).where(Activity.id == activity_id, Activity.trip_id == trip_id))
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.get("", response_model=list[ActivityResponse])
def list_activities(trip_id: TripId, response: Response, db: Database, user: CurrentUser):
    get_member_trip(trip_id, user.id, db)
    response.headers["Cache-Control"] = "no-store"
    return db.scalars(select(Activity).where(Activity.trip_id == trip_id)
                      .order_by(*activity_order())).all()


@router.post("", response_model=ActivityResponse, status_code=201)
def create_activity(trip_id: TripId, payload: ActivityInput, response: Response, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    validate_day(payload, trip)
    count = db.scalar(select(func.count()).select_from(Activity).where(Activity.trip_id == trip_id))
    if count >= MAX_ACTIVITIES:
        raise HTTPException(status_code=409, detail="Trip activity limit reached")
    activity = Activity(**payload.model_dump(), trip_id=trip_id, created_by=user.id)
    activity.position = next_position(trip_id, payload.activity_date, db)
    db.add(activity)
    commit_transaction(db)
    db.refresh(activity)
    response.headers["Cache-Control"] = "no-store"
    return activity


@router.post("/reorder", status_code=204)
def reorder_activities(trip_id: TripId, payload: ActivityOrder, db: Database, user: CurrentUser):
    get_member_trip(trip_id, user.id, db, lock=True)
    rows = db.scalars(select(Activity).where(
        Activity.trip_id == trip_id, Activity.activity_date == payload.activity_date)).all()
    if len(set(payload.activity_ids)) != len(payload.activity_ids) or set(payload.activity_ids) != {row.id for row in rows}:
        raise HTTPException(status_code=409, detail="Activity list changed; refresh before reordering")
    positions = {activity_id: index for index, activity_id in enumerate(payload.activity_ids)}
    for row in rows:
        row.position = positions[row.id]
    commit_transaction(db)
    return Response(status_code=204)


@router.get("/{activity_id}", response_model=ActivityResponse)
def read_activity(trip_id: TripId, activity_id: TripId, response: Response, db: Database, user: CurrentUser):
    get_member_trip(trip_id, user.id, db)
    response.headers["Cache-Control"] = "no-store"
    return find_activity(trip_id, activity_id, db)


@router.put("/{activity_id}", response_model=ActivityResponse)
def update_activity(trip_id: TripId, activity_id: TripId, payload: ActivityInput,
                    response: Response, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    validate_day(payload, trip)
    activity = find_activity(trip_id, activity_id, db)
    if activity.activity_date != payload.activity_date:
        activity.position = next_position(trip_id, payload.activity_date, db)
    for field, value in payload.model_dump().items():
        setattr(activity, field, value)
    commit_transaction(db)
    db.refresh(activity)
    response.headers["Cache-Control"] = "no-store"
    return activity


@router.delete("/{activity_id}", status_code=204)
def delete_activity(trip_id: TripId, activity_id: TripId, db: Database, user: CurrentUser):
    get_member_trip(trip_id, user.id, db, lock=True)
    db.delete(find_activity(trip_id, activity_id, db))
    commit_transaction(db)
    return Response(status_code=204)
