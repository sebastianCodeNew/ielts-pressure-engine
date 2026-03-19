from app.core.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT name FROM sqlite_master WHERE type="table"'))
        tables = result.fetchall()
        print('Database tables:')
        for table in tables:
            print(f'  - {table[0]}')
except Exception as e:
    print(f'❌ Database error: {e}')
