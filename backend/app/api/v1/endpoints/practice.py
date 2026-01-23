from fastapi import APIRouter

router = APIRouter()

@router.get("/topics")
def get_topics():
    return [
        {"id": "work", "name": "Work & Education", "level": "Easy", "part": "PART_1", "desc": "Talk about your job, studies, and future plans."},
        {"id": "hometown", "name": "Hometown", "level": "Easy", "part": "PART_1", "desc": "Describe where you live and what you like about it."},
        {"id": "hobbies", "name": "Hobbies & Interests", "level": "Easy", "part": "PART_1", "desc": "Discuss your free time activities and sports."},
        {"id": "events", "name": "Memorable Events", "level": "Medium", "part": "PART_2", "desc": "Describe a special occasion you attended recently."},
        {"id": "place", "name": "Beautiful Places", "level": "Medium", "part": "PART_2", "desc": "Talk about a landscape or building that inspired you."},
        {"id": "tech", "name": "Technology Impact", "level": "Hard", "part": "PART_3", "desc": "Deep dive into how AI and social media change society."},
        {"id": "env", "name": "Environmental Policy", "level": "Hard", "part": "PART_3", "desc": "Analyze global warming and sustainability challenges."}
    ]
