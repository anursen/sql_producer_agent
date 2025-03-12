from fastapi import APIRouter
from services.database_service import DatabaseService

router = APIRouter(prefix="/api", tags=["api"])
db_service = DatabaseService()

@router.post("/query")
async def execute_query(query: str):
    return await db_service.execute_query(query)
