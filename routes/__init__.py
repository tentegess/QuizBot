from fastapi import FastAPI
from .main import main_router
from .guild import guild_router
from .quiz import quiz_router

def init_routes(app: FastAPI):
    app.include_router(main_router)
    app.include_router(guild_router)
    app.include_router(quiz_router)
