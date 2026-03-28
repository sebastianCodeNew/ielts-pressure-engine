import re
import json
from app.core.logger import logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, ExamSession
from app.core.agent import llm
from langchain_core.prompts import PromptTemplate

router = APIRouter()

@router.get("/{session_id}/hint")
def get_hint(session_id: str, db: Session = Depends(get_db)):
    # 1. Get Current Prompt
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    current_prompt = session.current_prompt
    
    # 2. Ask LLM for assistance
    try:
        hint_prompt = PromptTemplate.from_template(
            """
            You are a helpful IELTS tutor. The student is stuck on this question: "{prompt}".
            
            Provide structured help in JSON format (do not use markdown blocks, just raw JSON):
            {{
                "vocabulary": ["word1 (definition)", "word2 (definition)", "word3"],
                "starter": "One way to start your answer is...",
                "grammar_tip": "Remember to use..."
            }}
            Keep it simple and encouraging.
            """
        )
        
        response = llm.invoke(hint_prompt.format(prompt=current_prompt))
        
        content = response.content.strip()
        
        # Robust JSON Extraction
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                content = match.group(0)
        
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"Hint generation failed: {e}", exc_info=True)
        return {
            "vocabulary": ["Interesting", "Challenging", "Experience"],
            "starter": "That is an interesting question...",
            "grammar_tip": "Try to use full sentences."
        }
