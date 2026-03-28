import sqlite3
import os

DB_PATH = "translation_memory.db"

# Persistent connection (v12.0)
_conn = None

def get_connection():
    global _conn
    if _conn is None:
        # check_same_thread=False allows sharing between FastAPI request threads
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Enable WAL mode for the cache too
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn

def init_db():
    """
    Creates the table if it doesn't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            indo_text TEXT PRIMARY KEY,
            eng_text TEXT
        )
    """)
    conn.commit()

def get_cached_translation(indo_text: str) -> str | None:
    """
    Checks if we have seen this phrase before.
    """
    cleaned_text = indo_text.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT eng_text FROM translations WHERE indo_text = ?", (cleaned_text,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return None

def save_translation_to_cache(indo_text: str, eng_text: str):
    """
    Saves a new translation for future speed.
    """
    cleaned_text = indo_text.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO translations (indo_text, eng_text) VALUES (?, ?)", 
        (cleaned_text, eng_text)
    )
    conn.commit()

def close_cache_connection():
    """
    Closes the persistent connection, called during app shutdown.
    """
    global _conn
    if _conn:
        _conn.close()
        _conn = None