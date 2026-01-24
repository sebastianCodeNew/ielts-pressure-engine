from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, JSON, ForeignKey, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

SQLITE_URL = "sqlite:///./ielts_pressure.db"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True) 
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    exam_sessions = relationship("ExamSession", back_populates="user")
    vocabulary = relationship("VocabularyItem", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    
    # Stats
    total_exams_taken = Column(Integer, default=0)
    average_band_score = Column(Float, default=0.0)

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    
    id = Column(String, primary_key=True, index=True) 
    user_id = Column(String, ForeignKey("users.id"))
    
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="IN_PROGRESS") 
    
    exam_type = Column(String, default="FULL_MOCK") 
    current_part = Column(String, default="PART_1") 
    current_prompt = Column(String, nullable=True) # NEW
    
    # Overall Scores
    overall_band_score = Column(Float, nullable=True)
    fluency_score = Column(Float, nullable=True)
    coherence_score = Column(Float, nullable=True) # NEW
    lexical_resource_score = Column(Float, nullable=True)
    grammatical_range_score = Column(Float, nullable=True)
    pronunciation_score = Column(Float, nullable=True)
    
    user = relationship("User", back_populates="exam_sessions")
    attempts = relationship("QuestionAttempt", back_populates="session")

class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("exam_sessions.id"))
    
    part = Column(String) 
    question_text = Column(String)
    
    audio_path = Column(String, nullable=True)
    transcript = Column(String, nullable=True)
    duration_seconds = Column(Float)
    
    wpm = Column(Float)
    coherence_score = Column(Float)
    hesitation_ratio = Column(Float)
    lexical_diversity = Column(Float, nullable=True) 
    grammar_complexity = Column(Float, nullable=True) 
    pronunciation_score = Column(Float, nullable=True) 
    
    feedback_markdown = Column(String, nullable=True)
    improved_response = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ExamSession", back_populates="attempts")

class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    word = Column(String, index=True)
    definition = Column(String)
    context_sentence = Column(String, nullable=True)
    
    mastery_level = Column(Integer, default=0) 
    last_reviewed_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="vocabulary")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    achievement_code = Column(String) 
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="achievements")

class SessionModel(Base):
    __tablename__ = "sessions_legacy" 
    session_id = Column(String, primary_key=True, index=True)
    stress_level = Column(Float, default=0.0)
    current_difficulty = Column(Integer, default=1)
    consecutive_failures = Column(Integer, default=0)
    fluency_trend = Column(String, default="stable")
    current_prompt = Column(String, default="Describe the room you are in right now.")
    history_json = Column(JSON, default=list)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # MIGRATION LOGIC
    with engine.connect() as conn:
        res = conn.execute(text("PRAGMA table_info(question_attempts)"))
        cols_qa = [row[1] for row in res]
        
        if "lexical_diversity" not in cols_qa:
            conn.execute(text("ALTER TABLE question_attempts ADD COLUMN lexical_diversity FLOAT"))
        if "grammar_complexity" not in cols_qa:
            conn.execute(text("ALTER TABLE question_attempts ADD COLUMN grammar_complexity FLOAT"))
        if "pronunciation_score" not in cols_qa:
            conn.execute(text("ALTER TABLE question_attempts ADD COLUMN pronunciation_score FLOAT"))
        
        res = conn.execute(text("PRAGMA table_info(exam_sessions)"))
        cols_es = [row[1] for row in res]
        if "coherence_score" not in cols_es:
            conn.execute(text("ALTER TABLE exam_sessions ADD COLUMN coherence_score FLOAT"))
        if "current_prompt" not in cols_es:
            conn.execute(text("ALTER TABLE exam_sessions ADD COLUMN current_prompt TEXT"))
            
        conn.commit()
    print("--- Database Schema Verified & Migrated ---")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
