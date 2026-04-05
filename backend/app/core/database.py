from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, JSON, ForeignKey, DateTime, text, Text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
from app.core.config import settings

from sqlalchemy import event
from app.core.logger import logger

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 120}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON") # v16.0: Ensure integrity
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True) 
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    exam_sessions = relationship("ExamSession", back_populates="user", cascade="all, delete-orphan")
    vocabulary = relationship("VocabularyItem", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    
    # Stats
    total_exams_taken = Column(Integer, default=0)
    average_band_score = Column(Float, default=0.0)
    
    # Preferences (DEFAULT TO BAND 9 per User Request)
    target_band = Column(String, default="9.0")
    weakness = Column(String, default="General")

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    
    id = Column(String, primary_key=True, index=True) 
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="IN_PROGRESS") 
    
    exam_type = Column(String, default="FULL_MOCK") 
    current_part = Column(String, default="PART_1") 
    current_prompt = Column(String, nullable=True) 
    current_prompt_translated = Column(String, nullable=True)
    initial_keywords = Column(JSON, nullable=True) 
    
    # Overall Scores (v3.0 - Session Summary)
    overall_band_score = Column(Float, nullable=True)
    fluency_score = Column(Float, nullable=True)
    coherence_score = Column(Float, nullable=True) 
    lexical_resource_score = Column(Float, nullable=True)
    grammatical_range_score = Column(Float, nullable=True)
    pronunciation_score = Column(Float, nullable=True)

    stress_level = Column(Float, default=0.5) 
    consecutive_failures = Column(Integer, default=0)
    fluency_trend = Column(String, default="stable") 
    
    user = relationship("User", back_populates="exam_sessions")
    attempts = relationship("QuestionAttempt", back_populates="session", cascade="all, delete-orphan")

class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("exam_sessions.id", ondelete="CASCADE"), index=True)
    
    part = Column(String) 
    question_text = Column(String)
    transcript = Column(Text, nullable=True) 
    duration_seconds = Column(Float)
    
    wpm = Column(Float)
    coherence_score = Column(Float)
    hesitation_ratio = Column(Float)
    lexical_diversity = Column(Float, nullable=True) 
    grammar_complexity = Column(Float, nullable=True) 
    pronunciation_score = Column(Float, nullable=True) 
    
    feedback_markdown = Column(String, nullable=True)
    feedback_translated = Column(String, nullable=True)
    improved_response = Column(String, nullable=True)
    improved_response_translated = Column(String, nullable=True)
    question_translated = Column(String, nullable=True)
    transcript_translated = Column(Text, nullable=True)
    
    target_keywords = Column(JSON, nullable=True) 
    keywords_hit = Column(JSON, nullable=True) 
    
    checkpoint_words_required = Column(JSON, nullable=True) 
    checkpoint_words_translated = Column(JSON, nullable=True) 
    checkpoint_words_meanings = Column(JSON, nullable=True) 
    checkpoint_words_hit = Column(JSON, nullable=True) 
    checkpoint_compliance_score = Column(Float, nullable=True) 
    
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ExamSession", back_populates="attempts")

class VocabularyItem(Base):
    """Refined single-source word bank for SM-2 training."""
    __tablename__ = "vocabulary_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    word = Column(String, index=True)
    word_translated = Column(String, nullable=True)
    definition = Column(String, nullable=True)
    definition_translated = Column(String, nullable=True)
    context_sentence = Column(String, nullable=True)
    source_type = Column(String, default="MANUAL")
    
    mastery_level = Column(Integer, default=0) 
    last_reviewed_at = Column(DateTime, default=datetime.utcnow)
    
    # Spaced Repetition (SM-2) - Initialized for learning
    next_review_at = Column(DateTime, default=datetime.utcnow)
    interval_days = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    
    user = relationship("User", back_populates="vocabulary")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    achievement_code = Column(String) 
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="achievements")

class ErrorLog(Base):
    """Tracks specific micro-skill errors for targeted learning."""
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    error_type = Column(String, index=True)  # e.g., "Subject-Verb Agreement"
    count = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, nullable=True)  # Optional: track which session

# --- DEPRECATION NOTICE ---
# SessionModel is legacy. Use ExamSession and QuestionAttempt instead.
class SessionModel(Base):
    __tablename__ = "sessions_legacy" 
    session_id = Column(String, primary_key=True, index=True)
    # ... rest remains for backward compatibility if needed for data recovery
    stress_level = Column(Float, default=0.0)
    current_difficulty = Column(Integer, default=1)
    consecutive_failures = Column(Integer, default=0)
    fluency_trend = Column(String, default="stable")
    current_prompt = Column(String, default="Describe the room you are in right now.")
    history_json = Column(JSON, default=list)

def get_columns(conn, table_name):
    try:
        res = conn.execute(text(f"PRAGMA table_info({table_name})"))
        return [row[1] for row in res]
    except Exception as e:
        logger.error(f"Failed to get table info for {table_name}: {e}")
        return []

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Base.metadata.create_all failed: {e}")
    
    # MIGRATION LOGIC (Manual but robust)
    try:
        with engine.connect() as conn:
            # 1. Question Attempts
            cols_qa = get_columns(conn, "question_attempts")
            migrations_qa = {
                "lexical_diversity": "FLOAT",
                "grammar_complexity": "FLOAT",
                "pronunciation_score": "FLOAT",
                "audio_path": "TEXT",
                "improved_response": "TEXT",
                "improved_response_translated": "TEXT",
                "feedback_translated": "TEXT",
                "question_translated": "TEXT",
                "transcript_translated": "TEXT",
                "target_keywords": "JSON",
                "keywords_hit": "JSON",
                "checkpoint_words_required": "JSON",
                "checkpoint_words_translated": "JSON",
                "checkpoint_words_meanings": "JSON",
                "checkpoint_words_hit": "JSON",
                "checkpoint_compliance_score": "FLOAT"
            }
            for col, col_type in migrations_qa.items():
                if col not in cols_qa:
                    try:
                        conn.execute(text(f"ALTER TABLE question_attempts ADD COLUMN {col} {col_type}"))
                    except Exception as e:
                        if "duplicate column name" not in str(e).lower():
                            logger.warning(f"Migration error (question_attempts.{col}): {e}")
        
            # 2. Exam Sessions
            cols_es = get_columns(conn, "exam_sessions")
            migrations_es = {
                "coherence_score": "FLOAT",
                "current_prompt": "TEXT",
                "current_prompt_translated": "TEXT",
                "initial_keywords": "JSON"
            }
            for col, col_type in migrations_es.items():
                if col not in cols_es:
                    try:
                        conn.execute(text(f"ALTER TABLE exam_sessions ADD COLUMN {col} {col_type}"))
                    except Exception as e:
                        if "duplicate column name" not in str(e).lower():
                            logger.warning(f"Migration error (exam_sessions.{col}): {e}")
        
            # 3. Users
            cols_u = get_columns(conn, "users")
            if "target_band" not in cols_u:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN target_band VARCHAR DEFAULT '9.0'"))
                except Exception as e:
                    logger.warning(f"Migration skipped (users.target_band): {e}")
            if "weakness" not in cols_u:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN weakness VARCHAR DEFAULT 'General'"))
                except Exception as e:
                    logger.warning(f"Migration skipped (users.weakness): {e}")
        
            # 4. Vocabulary (Spaced Repetition Reset v8.0)
            cols_v = get_columns(conn, "vocabulary_items")
            migrations_v = {
                "next_review_at": "DATETIME",
                "interval_days": "INTEGER DEFAULT 1",
                "ease_factor": "FLOAT DEFAULT 2.5",
                "word_translated": "TEXT",
                "definition_translated": "TEXT",
                "source_type": "VARCHAR DEFAULT 'MANUAL'"
            }
            for col, col_type in migrations_v.items():
                if col not in cols_v:
                    try:
                        conn.execute(text(f"ALTER TABLE vocabulary_items ADD COLUMN {col} {col_type}"))
                        # Populate defaults for existing rows to prevent NULL errors
                        if col == "ease_factor":
                            conn.execute(text("UPDATE vocabulary_items SET ease_factor = 2.5 WHERE ease_factor IS NULL"))
                        if col == "interval_days":
                            conn.execute(text("UPDATE vocabulary_items SET interval_days = 1 WHERE interval_days IS NULL"))
                    except Exception as e:
                        if "duplicate column name" not in str(e).lower():
                            logger.warning(f"Migration error (vocabulary_items.{col}): {e}")
            
            # 5. Achievements & Error Logs (v12.0)
            cols_ach = get_columns(conn, "user_achievements")
            if "achievement_code" not in cols_ach:
                try:
                    conn.execute(text("ALTER TABLE user_achievements ADD COLUMN achievement_code TEXT"))
                except Exception as e:
                    logger.error(f"Migration skipped (user_achievements): {e}")

            cols_err = get_columns(conn, "error_logs")
            if "error_type" not in cols_err:
                try:
                    conn.execute(text("ALTER TABLE error_logs ADD COLUMN error_type TEXT"))
                    conn.execute(text("ALTER TABLE error_logs ADD COLUMN count INTEGER DEFAULT 1"))
                except Exception as e:
                    logger.error(f"Migration skipped (error_logs): {e}")

            conn.commit()
    except Exception as e:
        logger.error(f"Migration block failed completely: {e}")
    logger.info("--- Database Schema Verified & Migrated ---")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
