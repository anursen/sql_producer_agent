import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.agents.sql_matic import SQLQueryAssistant
import json

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize SQL assistant
sql_assistant = SQLQueryAssistant()

@app.get("/")
async def get_chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            query = await websocket.receive_text()
            
            # Process query and get result
            result = await sql_assistant.process_query(query)
            
            # Send response to client
            await websocket.send_json({
                "type": "response",
                "content": result
            })
            
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "content": str(e)
        })
    finally:
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
