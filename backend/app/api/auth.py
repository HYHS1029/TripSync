from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limit_requests
from app.core.security import create_access_token, hash_password, verify_password
from app.database import commit_transaction, get_db
from app.models.user import User
from app.schemas.auth import EmailVerificationConfirm, EmailVerificationRequest, LoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.email import EmailDeliveryError, send_email, send_verification_email


router = APIRouter(prefix="/auth", tags=["auth"])
# Unknown accounts still perform a real hash verification to limit timing leaks.
_DUMMY_PASSWORD_HASH = hash_password("tripsync-dummy-password-not-an-account")


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    condition = (
        (User.email == payload.identifier) & User.email_verified_at.is_not(None)
        if "@" in payload.identifier else User.username == payload.identifier
    )
    user = db.scalar(select(User).where(condition))
    limit_requests(db, ("login-account" if user else "login-unknown", str(user.id) if user else payload.identifier, 20, 300))
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, password_hash)
    if user is None or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect account or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


Database = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def verification_digest(token: str) -> str:
    return hashlib.sha256(b"tripsync-email:" + token.encode("ascii")).hexdigest()


def require_email_verification() -> None:
    if not get_settings().email_verification_enabled:
        raise HTTPException(404, "Email verification is not enabled")


@router.post("/email-verification/request", status_code=202, dependencies=[Depends(require_email_verification)])
def request_email_verification(payload: EmailVerificationRequest, db: Database, user: CurrentUser):
    limit_requests(db, ("email-password", str(user.id), 10, 600))
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect password")
    if user.email == payload.email and user.email_verified_at:
        raise HTTPException(409, "Email already verified")
    if not get_settings().smtp_host:
        raise HTTPException(503, "Email delivery is not configured")
    limit_requests(db,
        ("email-minute", str(user.id), 1, 60),
        ("email-hour", str(user.id), 5, 3600),
        ("email-recipient", str(payload.email).lower(), 3, 3600),
    )
    # Serialize resends. A user has only one pending token, regardless of history.
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    token = secrets.token_urlsafe(32)
    user.pending_email = str(payload.email)
    user.email_verification_token_hash = verification_digest(token)
    user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=get_settings().email_verification_expire_minutes,
    )
    try:
        send_verification_email(str(payload.email), user.username, token)
        if user.email and user.email_verified_at:
            send_email(user.email, "TripSync 信箱變更申請通知", (
                f"你好，{user.username}：\n\n你的帳號剛提出信箱變更申請。"
                "原信箱會保留至新信箱確認完成。若非本人操作，請立即檢查帳號安全。\n"
            ))
    except EmailDeliveryError:
        db.rollback()
        raise HTTPException(503, "Unable to send verification email") from None
    commit_transaction(db)
    return {"message": "Verification email sent"}


@router.post("/email-verification/confirm", response_model=UserResponse, dependencies=[Depends(require_email_verification)])
def confirm_email_verification(payload: EmailVerificationConfirm, db: Database, user: CurrentUser):
    limit_requests(db, ("email-confirm", str(user.id), 10, 600))
    now = datetime.now(timezone.utc)
    try:
        confirmed = db.execute(update(User).where(
            User.id == user.id,
            User.pending_email.is_not(None),
            User.email_verification_token_hash == verification_digest(payload.token),
            User.email_verification_expires_at > now,
        ).values(
            email=User.pending_email, email_verified_at=now, pending_email=None,
            email_verification_token_hash=None, email_verification_expires_at=None,
        ).returning(User.id).execution_options(synchronize_session=False)).scalar_one_or_none()
        if confirmed is None:
            raise HTTPException(400, "Verification link unavailable")
        commit_transaction(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email unavailable") from None
    db.refresh(user)
    return user
