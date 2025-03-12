from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import chat_routes, api_routes

app = FastAPI(title="SQL Compiler LLM Agent")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(chat_routes.router)
app.include_router(api_routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
