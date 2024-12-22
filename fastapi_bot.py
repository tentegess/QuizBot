import uvicorn
from fastapi import FastAPI
from routes import init_routes

app = FastAPI()
init_routes(app)

def start_fastapi():
    uvicorn.run(
        "fastapi_bot:app",
        host="localhost",
        port=5000,
        log_level="info",
        reload=True,
        reload_dirs=["templates", "static", "routes"]
    )

if __name__ == "__main__":
    start_fastapi()