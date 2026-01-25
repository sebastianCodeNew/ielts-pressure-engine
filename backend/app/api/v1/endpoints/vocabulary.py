from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db, VocabularyItem
from app.schemas import VocabularyItemSchema, VocabularyCreate

router = APIRouter()

@router.get("/", response_model=List[VocabularyItemSchema])
def get_vocabulary(user_id: str = "default_user", db: Session = Depends(get_db)):
    return db.query(VocabularyItem).filter(VocabularyItem.user_id == user_id).all()

@router.post("/", response_model=VocabularyItemSchema)
def add_vocabulary(item: VocabularyCreate, user_id: str = "default_user", db: Session = Depends(get_db)):
    # Check for duplicate
    existing = db.query(VocabularyItem).filter(
        VocabularyItem.user_id == user_id, 
        VocabularyItem.word == item.word
    ).first()
    
    if existing:
        # Update last_reviewed instead of duplicating (Idempotency)
        existing.last_reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    db_item = VocabularyItem(
        user_id=user_id,
        word=item.word,
        definition=item.definition,
        context_sentence=item.context_sentence
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.patch("/{item_id}/mastery")
def update_mastery(item_id: int, level: int, db: Session = Depends(get_db)):
    db_item = db.query(VocabularyItem).filter(VocabularyItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.mastery_level = level
    db.commit()
    return {"status": "success"}
