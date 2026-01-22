from fastapi import APIRouter
from app.api.v1.endpoints import exams, practice, users

api_router = APIRouter()

api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(practice.router, prefix="/practice", tags=["practice"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# For now, let's keep the existing logic in main.py working, 
# but this file establishes the pattern.
