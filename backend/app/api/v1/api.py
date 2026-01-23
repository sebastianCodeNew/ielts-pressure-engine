from fastapi import APIRouter
from app.api.v1.endpoints import exams, users, practice, vocabulary, study_plan

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(practice.router, prefix="/practice", tags=["practice"])
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])
api_router.include_router(study_plan.router, prefix="/study-plan", tags=["study-plan"])
