import sqlite3
from pathlib import Path

class DatabaseService:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "Chinook.db"
        
    async def execute_query(self, query: str):
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            return {"error": str(e)}
