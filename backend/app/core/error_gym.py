"""
Error Gym v4.0 - Targeted Micro-Drill Generator

This module generates AI-powered drills to remediate chronic grammar 
and vocabulary errors identified in the user's ErrorLog.
"""

from typing import List, Dict
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain.chat_models import ChatOpenAI
import os

class ErrorDrill(BaseModel):
    """A single correction drill exercise."""
    error_type: str = Field(description="The type of error being drilled (e.g., 'Subject-Verb Agreement')")
    sentence_with_error: str = Field(description="A sentence containing the common error")
    correct_sentence: str = Field(description="The corrected version of the sentence")
    explanation: str = Field(description="Brief explanation of why this is correct")
    
class ErrorGymSession(BaseModel):
    """A collection of drills for a single Error Gym session."""
    drills: List[ErrorDrill] = Field(description="List of 3-5 correction drills")
    focus_area: str = Field(description="The primary error type being addressed")

def generate_error_gym_drills(error_type: str, error_count: int = 3) -> ErrorGymSession:
    """
    Generate targeted correction drills based on a specific error type.
    
    Args:
        error_type: The type of grammar/vocabulary error (e.g., "Subject-Verb Agreement")
        error_count: Number of drills to generate
        
    Returns:
        ErrorGymSession with AI-generated drills
    """
    parser = PydanticOutputParser(pydantic_object=ErrorGymSession)
    
    prompt = PromptTemplate(
        template="""You are an expert IELTS English tutor. Generate {count} targeted correction exercises 
for an IELTS speaking student who frequently makes "{error_type}" errors.

Each drill should:
1. Present a sentence with the common error (marked with [ERROR])
2. Show the corrected version
3. Explain WHY the correction matters for IELTS speaking

Make the sentences relevant to IELTS speaking topics (Part 1: everyday life, Part 2: personal stories, Part 3: abstract ideas).

{format_instructions}
""",
        input_variables=["error_type", "count"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Use DeepInfra with Llama 3 for cost-effective generation
    llm = ChatOpenAI(
        model_name="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        openai_api_key=os.getenv("DEEPINFRA_API_KEY"),
        openai_api_base="https://api.deepinfra.com/v1/openai",
        temperature=0.7
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "error_type": error_type,
            "count": min(error_count, 5)  # Cap at 5 drills
        })
        return result
    except Exception as e:
        # Fallback to hardcoded drills if AI generation fails
        return ErrorGymSession(
            focus_area=error_type,
            drills=[
                ErrorDrill(
                    error_type=error_type,
                    sentence_with_error="The group of students [ERROR: are] here.",
                    correct_sentence="The group of students is here.",
                    explanation="Collective nouns like 'group' take singular verbs."
                ),
                ErrorDrill(
                    error_type=error_type,
                    sentence_with_error="Neither my brother nor my sister [ERROR: are] coming.",
                    correct_sentence="Neither my brother nor my sister is coming.",
                    explanation="With 'neither...nor', the verb agrees with the nearest subject."
                ),
                ErrorDrill(
                    error_type=error_type,
                    sentence_with_error="Everyone [ERROR: have] their own opinion.",
                    correct_sentence="Everyone has their own opinion.",
                    explanation="Indefinite pronouns like 'everyone' are singular."
                )
            ]
        )


def get_top_errors_for_user(db, user_id: str, limit: int = 3) -> List[Dict]:
    """
    Retrieve the top error types for a user from the ErrorLog.
    
    Args:
        db: SQLAlchemy database session
        user_id: The user's ID
        limit: Maximum number of error types to return
        
    Returns:
        List of dicts with error_type and count
    """
    from app.core.database import ErrorLog
    
    errors = db.query(ErrorLog).filter(
        ErrorLog.user_id == user_id
    ).order_by(ErrorLog.count.desc()).limit(limit).all()
    
    return [{"error_type": e.error_type, "count": e.count} for e in errors]
