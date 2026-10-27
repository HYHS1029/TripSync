'''
Author: Jacky Hsieh
Date: 2026-09-24 17:18:23
FilePath: \TripSync\backend\app\main.py
'''
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.dependencies import get_current_user
from app.api.trips import router as trips_router
from app.api.members import router as members_router
from app.api.activities import router as activities_router
from app.api.expenses import router as expenses_router
from app.api.maps import router as maps_router
from app.core.security import hash_password
from app.database import engine, get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse


# Create the FastAPI application
app = FastAPI(
    title="TripSync API",
    version="0.1.0",
)


# Allow the frontend development server to access the backend API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(trips_router)
app.include_router(members_router)
app.include_router(activities_router)
app.include_router(expenses_router)
app.include_router(maps_router)


@app.middleware("http")
async def private_response_headers(request, call_next):
    response = await call_next(request)
    # Include errors: private 404 responses must not become shared cache entries.
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_request, error: RequestValidationError):
    # FastAPI's default detail includes input values, potentially passwords/tokens.
    return JSONResponse(status_code=422, content={"detail": [
        {key: issue[key] for key in ("loc", "msg", "type")} for issue in error.errors()
    ]})


@app.get("/users/me", response_model=UserResponse, tags=["users"])
def read_current_user(
    response: Response,
    user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    return user


# Application health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Database health check
@app.get("/health/db")
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }


# Create a new user
@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(
            or_(
                User.email == payload.email,
                User.username == payload.username,
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    db.refresh(user)

    return user
