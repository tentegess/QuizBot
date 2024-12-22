from datetime import datetime, timedelta, timezone
from http.client import responses
import discord
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from model.session_model import SessionModel
from utils.auth import Oauth
from discord.ext.ipc import Client
from config.config import session_collection


load_dotenv()
main_router = APIRouter()
api = Oauth()
templates = Jinja2Templates(directory="templates")
print("Main routes initialized")
ipc = Client(secret_key="test")

@main_router.on_event("startup")
async def on_startup():
    await api.setup()


@main_router.get("/")
async def home(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_collection.find_one({"_id": ObjectId(session_id)}):
        return RedirectResponse(url="/guilds")

    guild_count = await ipc.request("guild_count")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "discord_url": api.discord_login_url,
        "count": guild_count.response
    })

@main_router.get("/login")
async def login(code: str):
    result = await api.get_token_response(code)

    if result is None:
        raise HTTPException(status_code=401, detail="brak uprawnień")

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
    result = session_collection.update_one(
        {"user_id": int(user_id)},
        {"$set": session.model_dump()},
        upsert=True
    )

    if result.upserted_id:
        doc_id = result.upserted_id
    else:
        session_doc = session_collection.find_one({"user_id": int(user_id)})
        doc_id = session_doc["_id"]

    response = RedirectResponse(url="/guilds")
    response.set_cookie(key="session_id", value=str(doc_id), httponly=True)
    return response

@main_router.get("/guilds")
async def guilds(request: Request):
    session_id = request.cookies.get("session_id")
    session = session_collection.find_one({"_id": ObjectId(session_id)})
    if not session_id or not session:
        raise HTTPException(status_code=401, detail="brak uprawnień")

    token = session.get("token")
    user = await api.get_user(token)

    if datetime.now() > session.get("token_expires_at") or user.get("code") == 0:
        if await api.reload(session_id, session.get("refresh_token")):
            return RedirectResponse(url="/guilds")
        else:
            return RedirectResponse(url="/logout")

    if "id" not in user:
        return RedirectResponse(url="/logout")
    user_guilds = await api.get_guilds(token)
    perms = []

    bot_guilds = await ipc.request("bot_guilds")

    for guild in user_guilds:
        if guild["id"] in bot_guilds.response["data"]:
            guild["url"] = "/server/" + str(guild["id"])
        else:
            guild["url"] = f"https://discord.com/oauth2/authorize?client_id=1308514751026036847&guild_id={guild['id']}"


        guild["icon"] = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}"
        is_admin = discord.Permissions(int(guild["permissions"])).administrator
        if is_admin or guild["owner"]:
            perms.append(guild)

    return templates.TemplateResponse(
        "guilds.html",
        {
            "request": request,
            "user": user["global_name"],
            "guilds": perms
        })

@main_router.get("/server/{guild_id}")
async def server(request: Request, guild_id: int):
    session_id = request.cookies.get("session_id")
    if not session_id or not session_collection.find_one({"_id": ObjectId(session_id)}):
        raise HTTPException(status_code=401, detail="brak uprawnień")

    stats = await ipc.request("guild_stats", guild_id=guild_id)

    return templates.TemplateResponse(
        "server.html",
        {
            "request": request,
            "name": stats.response["name"],
            "member_count": stats.response["member_count"],
            "id": guild_id,
        })

@main_router.get("/logout")
async def logout(session_id: str = Cookie(None)):
    session = session_collection.find_one({"_id": ObjectId(session_id)})
    if not session_id or not session:
        raise HTTPException(status_code=401, detail="brak uprawnień")

    token = session.get("token")

    response = RedirectResponse("/")
    response.delete_cookie(key="session_id", httponly=True)

    session_collection.delete_one({"_id": ObjectId(session_id)})
    await api.revoke_token(token)

    return response