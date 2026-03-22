import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routes import pages, auth_routes, job_htmx, job_api, user_api, billing

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pitch Deck Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
# Frontend Pages
app.include_router(pages.router)

# Auth Routes
app.include_router(auth_routes.router)

# HTMX Routes (Dynamic Front-end form processing)
app.include_router(job_htmx.router)

# Core API Routes
app.include_router(job_api.router)
app.include_router(user_api.router)

# Billing Routes
app.include_router(billing.router)
