from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db, VocabularyItem
from app.core.config import settings
from app.schemas import VocabularyItemSchema, VocabularyCreate
from datetime import datetime
from app.core.spaced_repetition import calculate_next_review

from app.core.translator import translate_to_indonesian_async

router = APIRouter()


@router.get("/", response_model=List[VocabularyItemSchema])
def get_vocabulary(db: Session = Depends(get_db)):
    user_id = settings.DEFAULT_USER_ID
    return db.query(VocabularyItem).filter(VocabularyItem.user_id == user_id).all()


@router.post("/", response_model=VocabularyItemSchema)
async def add_vocabulary(item: VocabularyCreate, db: Session = Depends(get_db)):
    user_id = settings.DEFAULT_USER_ID
    # Normalize for consistency
    word_norm = item.word.strip().lower()

    # Check for duplicate
    existing = (
        db.query(VocabularyItem)
        .filter(VocabularyItem.user_id == user_id, VocabularyItem.word == word_norm)
        .first()
    )

    if existing:
        # Update last_reviewed instead of duplicating (Idempotency)
        existing.last_reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # NEW: Automated translation for manual entries
    try:
        word_tr = await translate_to_indonesian_async(word_norm)
        def_tr = await translate_to_indonesian_async(item.definition)
    except Exception:
        word_tr = None
        def_tr = None

    db_item = VocabularyItem(
        user_id=user_id,
        word=word_norm,
        word_translated=word_tr,
        definition=item.definition,
        definition_translated=def_tr,
        context_sentence=item.context_sentence,
        source_type="MANUAL",
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/{item_id}/review")
def review_vocabulary(item_id: int, quality: int, db: Session = Depends(get_db)):
    """
    Updates a word using SM-2 logic based on user recall quality (0-5).
    """
    db_item = db.query(VocabularyItem).filter(VocabularyItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not 0 <= quality <= 5:
        raise HTTPException(status_code=400, detail="Quality must be between 0 and 5")

    # Connect to SM-2 Engine
    calculate_next_review(db_item, quality)

    db.commit()
    return {"status": "success", "next_review": db_item.next_review_at}


@router.patch("/{item_id}/mastery")
def update_mastery_legacy(item_id: int, level: int, db: Session = Depends(get_db)):
    """Legacy endpoint for direct mastery updates."""
    db_item = db.query(VocabularyItem).filter(VocabularyItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.mastery_level = min(100, max(0, level))
    db.commit()
    return {"status": "success"}
