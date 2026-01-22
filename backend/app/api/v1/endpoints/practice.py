from fastapi import APIRouter

router = APIRouter()

@router.get("/topics")
def get_topics():
    return [
        {"id": "work", "name": "Work & Education", "level": "General"},
        {"id": "tech", "name": "Technology & AI", "level": "Advanced"},
        {"id": "env", "name": "Environment", "level": "Academic"},
        {"id": "hobbies", "name": "Hobbies & Leisure", "level": "General"}
    ]
