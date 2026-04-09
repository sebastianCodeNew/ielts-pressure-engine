from fastapi import APIRouter, Depends
from app.core.logger import logger
from sqlalchemy.orm import Session
from app.core.database import get_db, QuestionAttempt, ExamSession
from app.schemas import StudyPlan, StudyPlanItem
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
import os
import json
import re
from datetime import datetime

router = APIRouter()

llm = ChatOpenAI(
    base_url="https://api.deepinfra.com/v1/openai",
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    model="meta-llama/Llama-3.2-3B-Instruct",
    temperature=0.3,
    timeout=60,
)


@router.get("/", response_model=StudyPlan)
def generate_study_plan(user_id: str = "default_user", db: Session = Depends(get_db)):
    # 1. Fetch recent performance
    recent_attempts = (
        db.query(QuestionAttempt)
        .filter(
            QuestionAttempt.session_id.in_(
                db.query(ExamSession.id).filter(ExamSession.user_id == user_id)
            )
        )
        .order_by(QuestionAttempt.created_at.desc())
        .limit(10)
        .all()
    )

    # 2. Extract weak points
    summary = "User performance summary:\n"
    if not recent_attempts:
        summary += "- No data yet. User is a beginner."
    else:
        for att in recent_attempts:
            summary += f"- Part {att.part}: WPM={att.wpm}, Coherence={att.coherence_score}, Lexical={att.lexical_diversity}\n"

    # 3. Prompt AI for a 7-day plan
    prompt = f"""
    Based on the following IELTS Speaking performance data, generate a personalized 7-day study plan for the user.
    Focus on their weak areas.
    
    DATA:
    {summary}
    
    Format the response EXACTLY as a JSON list of 7 items.
    Each item must HAVE:
    - day: "Day 1", "Day 2", etc.
    - focus: High-level goal (e.g., "Fluency & Connector Words")
    - tasks: List of 3 specific actionable tasks.
    
    CRITICAL: Output ONLY the JSON. No conversational filler.
    """

    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        content = response.content.strip()

        # Robust JSON Extraction
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            clean_json = json_match.group(1).strip()
        else:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                clean_json = match.group(0)
            else:
                clean_json = content

        plan_data = json.loads(clean_json)

        items = [
            StudyPlanItem(day=d["day"], focus=d["focus"], tasks=d["tasks"])
            for d in plan_data
        ]

        return StudyPlan(user_id=user_id, created_at=datetime.utcnow(), plan=items)
    except Exception as e:
        logger.error(f"STUDY PLAN ERROR: {e}", exc_info=True)
        # Fallback plan
        return StudyPlan(
            user_id=user_id,
            created_at=datetime.utcnow(),
            plan=[
                StudyPlanItem(
                    day=f"Day {i + 1}",
                    focus="General Practice",
                    tasks=["Practice Part 1", "Review Vocab", "Record yourself"],
                )
                for i in range(7)
            ],
        )
