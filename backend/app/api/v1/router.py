# backend/app/api/v1/router.py

from fastapi import APIRouter
from app.api.v1.endpoints import documents, transactions, dashboard

# Create the main v1 API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(documents.router)
api_router.include_router(transactions.router)
api_router.include_router(dashboard.router)
