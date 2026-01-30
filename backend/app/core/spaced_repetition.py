"""
Spaced Repetition Engine (SM-2 Algorithm)
Calculates the next review date for vocabulary items based on user performance.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import VocabularyItem

def calculate_next_review(item: VocabularyItem, quality: int) -> VocabularyItem:
    """
    Updates a vocabulary item's spaced repetition schedule.
    
    Args:
        item: The VocabularyItem to update.
        quality: User's self-assessment of recall (0-5).
                 0-2 = Fail (reset interval)
                 3 = Barely recalled
                 4 = Recalled with effort
                 5 = Perfect recall
    
    Returns:
        The updated VocabularyItem.
    """
    if quality < 3:
        # Failed recall - reset
        item.interval_days = 1
        item.ease_factor = max(1.3, item.ease_factor - 0.2)
    else:
        # Successful recall
        if item.interval_days == 1:
            item.interval_days = 6
        else:
            item.interval_days = int(item.interval_days * item.ease_factor)
        
        # Adjust ease factor based on quality
        item.ease_factor = max(1.3, item.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    item.next_review_at = datetime.utcnow() + timedelta(days=item.interval_days)
    item.last_reviewed_at = datetime.utcnow()
    
    # Update mastery level (0-100 scale)
    if quality >= 4:
        item.mastery_level = min(100, item.mastery_level + 10)
    elif quality < 3:
        item.mastery_level = max(0, item.mastery_level - 15)
    
    return item

def get_due_vocabulary(db: Session, user_id: str, limit: int = 3) -> list[VocabularyItem]:
    """
    Retrieves vocabulary items that are due for review.
    
    Args:
        db: Database session.
        user_id: The user's ID.
        limit: Maximum number of items to return.
    
    Returns:
        List of VocabularyItem objects due for review.
    """
    now = datetime.utcnow()
    due_items = db.query(VocabularyItem).filter(
        VocabularyItem.user_id == user_id,
        VocabularyItem.next_review_at <= now
    ).order_by(VocabularyItem.next_review_at.asc()).limit(limit).all()
    
    return due_items
