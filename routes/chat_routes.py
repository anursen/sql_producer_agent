from fastapi import APIRouter, WebSocket
from services.llm_service import LLMService

router = APIRouter(prefix="/chat", tags=["chat"])
llm_service = LLMService()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await llm_service.process_message(data)
            await websocket.send_text(response)
    except Exception as e:
        print(f"WebSocket error: {e}")
