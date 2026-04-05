import sqlite3
import os
import re
from contextlib import contextmanager
from app.core.logger import logger

DB_PATH = "translation_memory.db"

@contextmanager
def get_db_connection():
    """
    Thread-safe context manager for SQLite connections. (v16.0 - Resiliency Hardening)
    Opening/closing a connection per task is safest for concurrent async writes in SQLite.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        # WAL mode is persistent after the first time, but initializing it per connection
        # ensures consistency even if the DB file was just created.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        yield conn
    except Exception as e:
        logger.error(f"Cache DB Connection Error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_cache_db():
    """
    Initializes the translation memory database with unambiguous naming.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_memory (
                source_text TEXT PRIMARY KEY,
                target_text TEXT
            )
        """)
        conn.commit()

def _normalize_text(text: str) -> str:
    """Consistently normalizes text for cache lookups (v16.0 - High Performance)."""
    if not text:
        return ""
    # 1. Lowercase
    t = text.lower().strip()
    # 2. Collapse internal whitespace 
    t = re.sub(r'\s+', ' ', t)
    # 3. Strip non-alphanumeric punctuation from start/end to increase cache hits
    # (e.g. "Hometown." == "Hometown!")
    t = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', t)
    return t.strip()

def get_cached_translation(source_text: str) -> str | None:
    cleaned_text = _normalize_text(source_text)
    if not cleaned_text:
        return None
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT target_text FROM translation_memory WHERE source_text = ?", (cleaned_text,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Cache Search Error: {e}")
        return None

def save_translation_to_cache(source_text: str, target_text: str):
    cleaned_text = _normalize_text(source_text)
    if not cleaned_text or not target_text:
        return
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO translation_memory (source_text, target_text) VALUES (?, ?)", 
                (cleaned_text, target_text)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Cache Save Error: {e}")