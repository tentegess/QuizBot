import uvicorn
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from routes import init_routes
from fastapi.exception_handlers import http_exception_handler

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
init_routes(app)

def start_fastapi():
    uvicorn.run(
        "fastapi_bot:app",
        host="localhost",
        port=5000,
        log_level="info",
        reload=True,
        reload_dirs=["templates", "static/css", "static/images"]
    )

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 307:
        return await http_exception_handler(request, exc)

    return RedirectResponse(url=f"/error?status_code={exc.status_code}&detail={exc.detail}")

if __name__ == "__main__":
    start_fastapi()