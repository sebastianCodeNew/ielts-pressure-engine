from fastapi import APIRouter
from pydantic import BaseModel
from app.core.translator import translate_to_indonesian_async
from app.core.logger import logger

router = APIRouter()


class TranslationRequest(BaseModel):
    text: str


class TranslationResponse(BaseModel):
    translated_text: str


@router.post("/", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    General purpose translation endpoint for the frontend.
    """
    if not request.text:
        return TranslationResponse(translated_text="")

    try:
        translated = await translate_to_indonesian_async(request.text)
        return TranslationResponse(translated_text=translated)
    except Exception as e:
        logger.error(f"Translation endpoint error: {e}")
        # Fallback to original text if translation fails
        return TranslationResponse(translated_text=request.text)
