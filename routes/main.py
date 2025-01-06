from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from model.session_model import SessionModel
from model.user_model import UserModel
from utils.auth import api
from utils.discord_api import discord_api
from config.config import session_collection, user_collection

load_dotenv()
main_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@main_router.on_event("startup")
async def on_startup():
    await api.setup()
    await discord_api.setup()

@main_router.on_event("shutdown")
async def shutdown_event():
    await api.close()
    await discord_api.close()


@main_router.get("/")
async def home(request: Request):
    session_id = request.cookies.get("session_id")
    session = await session_collection.find_one({"_id": ObjectId(session_id)})
    if session_id and session:
        return RedirectResponse(url="/guilds")

    guilds = await discord_api.fetch_guilds()
    guild_count = len(guilds)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "discord_url": api.discord_login_url,
        "count": guild_count,
        "is_not_logged": True
    })

@main_router.get("/login")
async def login(code: str):
    result = await api.get_token_response(code)

    if result is None:
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    token, refresh_token, expires_in = result
    user = await api.get_user(token)

    user_id = user.get('id')
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    session = SessionModel(
        token=token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at,
        user_id=user_id
    )
    result = await session_collection.update_one(
        {"user_id": int(user_id)},
        {"$set": session.model_dump()},
        upsert=True
    )

    user_name_model = UserModel(
        user_id=user_id,
        username=user.get('username'),
    )
    await user_collection.update_one(
        {"user_id": int(user_id)},
        {"$set": user_name_model.model_dump()},
        upsert=True
    )

    if result.upserted_id:
        doc_id = result.upserted_id
    else:
        session_doc = await session_collection.find_one({"user_id": int(user_id)})
        doc_id = session_doc["_id"]

    response = RedirectResponse(url="/guilds")
    response.set_cookie(key="session_id", value=str(doc_id), httponly=True)
    return response

@main_router.get("/logout")
async def logout(session_id: str = Cookie(None)):
    session = await session_collection.find_one({"_id": ObjectId(session_id)})
    if not session_id or not session:
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    token = session.get("token")

    response = RedirectResponse("/")
    response.delete_cookie(key="session_id", httponly=True)

    await session_collection.delete_one({"_id": ObjectId(session_id)})
    await api.revoke_token(token)

    return response

@main_router.get("/error")
async def error_page(request: Request):
    status_code = request.query_params.get("status_code", "Unknown")
    detail = request.query_params.get("detail", "Unknown error")

    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": status_code, "detail": detail}
    )