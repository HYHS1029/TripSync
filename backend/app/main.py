'''
Author: Jacky Hsieh
Date: 2026-09-24 17:18:23
FilePath: \TripSync\backend\app\main.py
'''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine


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


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/health/db")
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }