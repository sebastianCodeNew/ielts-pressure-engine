import sqlite3
import os

DB_PATH = "translation_memory.db"

def init_db():
    """
    Creates the table if it doesn't exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
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
    
    with sqlite3.connect(DB_PATH) as conn:
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
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # INSERT OR IGNORE means: if it exists, don't crash, just skip.
        cursor.execute(
            "INSERT OR REPLACE INTO translations (indo_text, eng_text) VALUES (?, ?)", 
            (cleaned_text, eng_text)
        )
        conn.commit()