from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select

from app.api.trips import CurrentUser, Database, TripId, get_member_trip, require_owner
from app.core.security import create_invitation_token, hash_invitation_token
from app.database import commit_transaction
from app.models.invitation import TripInvitation
from app.models.trip import Trip, TripMember
from app.models.user import User
from app.schemas.member import AcceptInvitation, InvitationCreated, InvitationResponse, MemberResponse
from app.schemas.trip import TripResponse


router = APIRouter(tags=["members"])
logger = logging.getLogger(__name__)
MAX_MEMBERS = 100
INVITATIONS_PER_HOUR = 10


@router.get("/trips/{trip_id}/members", response_model=list[MemberResponse])
def list_members(trip_id: TripId, response: Response, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db)
    response.headers["Cache-Control"] = "no-store"
    rows = db.execute(
        select(User.id, User.username, TripMember.joined_at)
        .join(TripMember, TripMember.user_id == User.id)
        .where(TripMember.trip_id == trip_id)
        .order_by((User.id == trip.owner_id).desc(), TripMember.joined_at, User.id)
    )
    return [MemberResponse(user_id=row.id, username=row.username, joined_at=row.joined_at,
                           is_owner=row.id == trip.owner_id) for row in rows]


@router.delete("/trips/{trip_id}/members/me", status_code=204)
def leave_trip(trip_id: TripId, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    if trip.owner_id == user.id:
        raise HTTPException(status_code=409, detail="The owner cannot leave their trip")
    db.delete(db.get(TripMember, (trip_id, user.id)))
    commit_transaction(db)
    logger.info("trip_member_left trip_id=%s user_id=%s", trip_id, user.id)
    return Response(status_code=204)


@router.delete("/trips/{trip_id}/members/{member_id}", status_code=204)
def remove_member(trip_id: TripId, member_id: TripId, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    require_owner(trip, user)
    if member_id == trip.owner_id:
        raise HTTPException(status_code=409, detail="The owner cannot be removed")
    member = db.get(TripMember, (trip_id, member_id))
    if member:
        db.delete(member)
    commit_transaction(db)
    logger.info("trip_member_removed trip_id=%s actor_id=%s user_id=%s", trip_id, user.id, member_id)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/invitations", response_model=InvitationCreated, status_code=201)
def create_invitation(trip_id: TripId, response: Response, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    require_owner(trip, user)
    now = datetime.now(timezone.utc)
    recent = db.scalar(select(func.count()).select_from(TripInvitation).where(
        TripInvitation.trip_id == trip_id, TripInvitation.created_at > now - timedelta(hours=1)
    ))
    if recent >= INVITATIONS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Invitation creation limit reached", headers={"Retry-After": "3600"})
    token, digest = create_invitation_token()
    invitation = TripInvitation(trip_id=trip_id, token_hash=digest, expires_at=now + timedelta(days=7))
    db.add(invitation)
    commit_transaction(db)
    db.refresh(invitation)
    response.headers["Cache-Control"] = "no-store"
    return InvitationCreated(**InvitationResponse.model_validate(invitation).model_dump(), token=token)


@router.get("/trips/{trip_id}/invitations", response_model=list[InvitationResponse])
def list_invitations(trip_id: TripId, response: Response, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db)
    require_owner(trip, user)
    response.headers["Cache-Control"] = "no-store"
    return db.scalars(select(TripInvitation).where(TripInvitation.trip_id == trip_id)
                      .order_by(TripInvitation.id.desc()).limit(50)).all()


@router.delete("/trips/{trip_id}/invitations/{invitation_id}", status_code=204)
def revoke_invitation(trip_id: TripId, invitation_id: TripId, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    require_owner(trip, user)
    invitation = db.scalar(select(TripInvitation).where(
        TripInvitation.id == invitation_id, TripInvitation.trip_id == trip_id
    ))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(timezone.utc)
    commit_transaction(db)
    return Response(status_code=204)


@router.post("/invitations/accept", response_model=TripResponse)
def accept_invitation(payload: AcceptInvitation, response: Response, db: Database, user: CurrentUser):
    unavailable = HTTPException(status_code=404, detail="Invitation unavailable")
    invitation = db.scalar(select(TripInvitation).where(
        TripInvitation.token_hash == hash_invitation_token(payload.token)
    ))
    if invitation is None:
        raise unavailable
    # The shared trip lock serializes acceptance, revocation, removal and writes.
    trip = db.scalar(select(Trip).where(Trip.id == invitation.trip_id).with_for_update())
    if trip is None:
        raise unavailable
    db.refresh(invitation)
    now = datetime.now(timezone.utc)
    expires = invitation.expires_at.replace(tzinfo=timezone.utc) if invitation.expires_at.tzinfo is None else invitation.expires_at
    if invitation.revoked_at or expires <= now:
        raise unavailable
    member = db.get(TripMember, (trip.id, user.id))
    if invitation.accepted_by is not None:
        if invitation.accepted_by != user.id or member is None:
            raise unavailable
    elif member is None:
        count = db.scalar(select(func.count()).select_from(TripMember).where(TripMember.trip_id == trip.id))
        if count >= MAX_MEMBERS:
            raise HTTPException(status_code=409, detail="Trip member limit reached")
        db.add(TripMember(trip_id=trip.id, user_id=user.id))
        invitation.accepted_by = user.id
        invitation.accepted_at = now
        commit_transaction(db)
        logger.info("trip_member_joined trip_id=%s user_id=%s invitation_id=%s", trip.id, user.id, invitation.id)
    response.headers["Cache-Control"] = "no-store"
    return trip
