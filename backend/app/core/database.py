from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLITE_URL = "sqlite:///./ielts_pressure.db"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---

class SessionModel(Base):
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    stress_level = Column(Float, default=0.0)
    current_difficulty = Column(Integer, default=1)
    consecutive_failures = Column(Integer, default=0)
    fluency_trend = Column(String, default="stable")
    current_prompt = Column(String, default="Describe the room you are in right now.") # <--- NEW: Persist prompt
    history_json = Column(JSON, default=list) # Stores list of recent AttemptResults

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
