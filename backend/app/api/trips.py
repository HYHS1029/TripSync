from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.trip import Trip, TripMember
from app.models.activity import Activity
from app.models.user import User
from app.schemas.trip import TripCreate, TripResponse, TripUpdate


router = APIRouter(prefix="/trips", tags=["trips"])
Database = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
TripId = Annotated[int, Path(gt=0, le=2_147_483_647)]


def get_member_trip(trip_id: int, user_id: int, db: Session, *, lock: bool = False) -> Trip:
    if lock:
        # Lock the trip first, then check membership in a fresh statement. A JOIN
        # evaluated before waiting on a lock could retain a removed membership.
        trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update())
        if trip is None or db.get(TripMember, (trip_id, user_id)) is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        return trip
    trip = db.scalar(
        select(Trip)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(Trip.id == trip_id, TripMember.user_id == user_id)
    )
    if trip is None:
        # Do not reveal whether a private trip exists to non-members.
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


def require_owner(trip: Trip, user: User) -> None:
    if trip.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the trip owner can manage this trip")


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, response: Response, db: Database, user: CurrentUser):
    trip = Trip(**payload.model_dump(), owner_id=user.id)
    try:
        db.add(trip)
        db.flush()
        db.add(TripMember(trip_id=trip.id, user_id=user.id))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(trip)
    response.headers["Cache-Control"] = "no-store"
    return trip


@router.get("", response_model=list[TripResponse])
def list_trips(response: Response, db: Database, user: CurrentUser):
    response.headers["Cache-Control"] = "no-store"
    return db.scalars(
        select(Trip)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(TripMember.user_id == user.id)
        .order_by(Trip.created_at.desc(), Trip.id.desc())
    ).all()


@router.get("/{trip_id}", response_model=TripResponse)
def read_trip(trip_id: TripId, response: Response, db: Database, user: CurrentUser):
    response.headers["Cache-Control"] = "no-store"
    return get_member_trip(trip_id, user.id, db)


@router.patch("/{trip_id}", response_model=TripResponse)
def update_trip(
    trip_id: TripId, payload: TripUpdate, response: Response, db: Database, user: CurrentUser
):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    require_owner(trip, user)
    changes = payload.model_dump(exclude_unset=True)
    start_date = changes.get("start_date", trip.start_date)
    end_date = changes.get("end_date", trip.end_date)
    if end_date < start_date:
        raise HTTPException(status_code=422, detail=[{
            "loc": ["body", "end_date"],
            "msg": "End date must be on or after start date",
            "type": "value_error",
        }])
    outside = db.scalar(select(Activity.id).where(
        Activity.trip_id == trip_id,
        (Activity.activity_date < start_date) | (Activity.activity_date > end_date),
    ).limit(1))
    if outside is not None:
        raise HTTPException(status_code=422, detail=[{
            "loc": ["body", "end_date"],
            "msg": "Trip dates must include all existing activities",
            "type": "activity_date_range",
        }])
    for field, value in changes.items():
        setattr(trip, field, value)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(trip)
    response.headers["Cache-Control"] = "no-store"
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: TripId, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    require_owner(trip, user)
    try:
        db.delete(trip)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
