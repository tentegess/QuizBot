import discord
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException, status, Form, Response
from fastapi.params import Depends
from fastapi.templating import Jinja2Templates
from requests import session
from model.settings_model import SettingsModel
from utils.auth import api
from utils.validate_session import validate_session_with_data
from utils.discord_api import discord_api
from config.config import settings_collection
import os

load_dotenv()
guild_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@guild_router.get("/guilds")
async def guilds(request: Request, data: dict = Depends(validate_session_with_data)):
    session = data['session']
    user = data['user']
    token = session.get("token")
    user_guilds = await api.get_guilds(token)
    bot_guilds = await discord_api.fetch_guilds()
    perms = []

    for guild in user_guilds:
        if guild["id"] in bot_guilds:
            guild["url"] = "/server/" + str(guild["id"])
        else:
            guild["url"] = os.environ.get('DISCORD_INVITE') +"&guild_id="+guild['id']

        if guild.get("icon"):
            guild["icon"] = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}"
        else:
            guild["icon"] = "https://cdn.discordapp.com/embed/avatars/0.png"
        is_admin = discord.Permissions(int(guild["permissions"])).administrator

        if is_admin or guild["owner"]:
            perms.append(guild)

    response = templates.TemplateResponse(
        "guilds.html",
        {
            "request": request,
            "user": user["global_name"],
            "guilds": perms
        })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

@guild_router.get("/server/{guild_id}")
async def server(request: Request, guild_id: str, data: dict = Depends(validate_session_with_data)):
    session = data['session']

    try:
        guild_id = int(guild_id)
        stats = await discord_api.fetch_guild_name(guild_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Serwer nie istnieje")
    user_guilds = await api.get_guilds(token=session.get("token"))
    guild = next((g for g in user_guilds if g["id"] == str(guild_id)), None)

    if guild is None:
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    settings = await settings_collection.find_one({"guild_id": guild_id})
    default_settings = {
        "guild_id": guild_id,
        "join_window_display_time": 5,
        "answer_display_time": 5,
        "results_display_time": 5,
        "show_results_per_question": False
    }
    if not settings:
        settings = default_settings

    is_admin = discord.Permissions(int(guild["permissions"])).administrator
    is_owner = guild["owner"]

    if not is_admin and not is_owner:
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    return templates.TemplateResponse(
        "server.html",
        {
            "request": request,
            "server_name": stats["name"],
            "settings": settings
        })

@guild_router.post("/server/{guild_id}")
async def update_server_settings(
        guild_id: str,
        join_window_display_time: int = Form(...),
        answer_display_time: int = Form(...),
        results_display_time: int = Form(...),
        show_results_per_question: bool = Form(False),
        data: dict = Depends(validate_session_with_data)
):
    session = data['session']

    user_guilds = await api.get_guilds(token=session.get("token"))
    guild = next((g for g in user_guilds if g["id"] == guild_id), None)

    if guild is None:
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    is_admin = discord.Permissions(int(guild["permissions"])).administrator
    is_owner = guild["owner"]

    if not is_admin and not is_owner:
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    try:
        settings_data = SettingsModel(
            guild_id=guild_id,
            join_window_display_time=join_window_display_time,
            answer_display_time=answer_display_time,
            results_display_time=results_display_time,
            show_results_per_question=show_results_per_question,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowe dane wejściowe: {e}")

    await settings_collection.update_one(
        {"guild_id": int(guild_id)},
        {"$set": settings_data.model_dump()},
        upsert=True
    )

    return {"message": "Ustawienia zostały zapisane pomyślnie"}