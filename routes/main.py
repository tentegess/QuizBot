import asyncio
from datetime import datetime, timedelta, timezone
from http.client import responses
import discord
from bson.objectid import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException, Cookie, status, File, UploadFile, Form
from fastapi.params import Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from requests import session
from typing import List
from model.session_model import SessionModel
from model.quiz_model import QuizModel
from model.question_model import QuestionModel
from model.option_model import OptionModel
from utils.auth import Oauth, api
from utils.validate_session import validate_session_without_data, validate_session_with_data
from utils.validate_quiz import validate_quiz_data, img_scaling
from utils.generate_unique_id import get_unique_access_code
from discord.ext.ipc import Client
from config.config import session_collection, quiz_collection, db, question_collection
import json
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorGridFSBucket


load_dotenv()
main_router = APIRouter()
templates = Jinja2Templates(directory="templates")
print("Main routes initialized")
ipc = Client(secret_key="test")

@main_router.on_event("startup")
async def on_startup():
    await api.setup()


@main_router.get("/")
async def home(request: Request):
    session_id = request.cookies.get("session_id")
    session = await session_collection.find_one({"_id": ObjectId(session_id)})
    if session_id and session:
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
    result = await session_collection.update_one(
        {"user_id": int(user_id)},
        {"$set": session.model_dump()},
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

@main_router.get("/guilds")
async def guilds(request: Request, data: dict = Depends(validate_session_with_data)):
    session = data['session']
    user = data['user']
    token = session.get("token")
    user_guilds = await api.get_guilds(token)
    bot_guilds = await ipc.request("bot_guilds")
    perms = []

    for guild in user_guilds:
        if guild["id"] in bot_guilds.response["data"]:
            guild["url"] = "/server/" + str(guild["id"])
        else:
            guild["url"] = f"https://discord.com/oauth2/authorize?client_id=1308514751026036847&guild_id={guild['id']}"

        if guild.get("icon"):
            guild["icon"] = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}"
        else:
            guild["icon"] = "https://cdn.discordapp.com/embed/avatars/0.png"
        is_admin = discord.Permissions(int(guild["permissions"])).administrator

        if is_admin or guild["owner"]:
            perms.append(guild)

    perms *= 100

    return templates.TemplateResponse(
        "guilds.html",
        {
            "request": request,
            "user": user["global_name"],
            "guilds": perms
        })

@main_router.get("/server/{guild_id}")
async def server(request: Request, guild_id: int, _: None = Depends(validate_session_without_data)):
    stats = await ipc.request("guild_stats", guild_id=guild_id)

    return templates.TemplateResponse(
        "server.html",
        {
            "request": request,
            "name": stats.response["name"],
            "member_count": stats.response["member_count"],
            "id": guild_id,
        })

@main_router.get("/new-quiz")
async def make_quiz(request: Request, _: None = Depends(validate_session_without_data)):
    return templates.TemplateResponse(
        "make_quiz.html",
        {
            "request": request,
        })


@main_router.post("/quiz/add")
async def save_quiz(
        title: str = Form(...),
        questions: str = Form(...),
        files: Optional[List[UploadFile]] = File(None),
        data: dict = Depends(validate_session_with_data)
):
    user = data['user']
    user_id = user.get("id")

    questions_data = json.loads(questions)
    if not validate_quiz_data(title, questions_data):
        raise HTTPException(status_code=400, detail="Niepoprawnie uzupełnione dane.")

    saved_questions = []
    for idx, question in enumerate(questions_data):
        image_url = None
        if files and idx < len(files):
            image_file = files[idx]
            file_contents = await image_file.read()

            file_contents = img_scaling(file_contents)
            fs = AsyncIOMotorGridFSBucket(db)
            grid_file_id = await fs.upload_from_stream(image_file.filename, file_contents)
            image_url = grid_file_id

        options = [
            OptionModel(option=answer['content'], is_correct=answer['is_correct'])
            for answer in question.get('answers', [])
        ]

        saved_question = QuestionModel(
            question=question['content'],
            options=options,
            image_url=image_url,
            time=question.get('time', 5)
        )
        saved_questions.append(saved_question)

    access_code = await get_unique_access_code()

    quiz = QuizModel(
        title=title,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        user_id=int(user_id),
        questions=saved_questions,
        access_code=access_code
    )

    quiz_dict = quiz.model_dump()
    quiz_id = await quiz_collection.insert_one(quiz_dict)
    return

@main_router.get("/logout")
async def logout(session_id: str = Cookie(None)):
    session = await session_collection.find_one({"_id": ObjectId(session_id)})
    if not session_id or not session:
        raise HTTPException(status_code=401, detail="brak uprawnień")

    token = session.get("token")

    response = RedirectResponse("/")
    response.delete_cookie(key="session_id", httponly=True)

    await session_collection.delete_one({"_id": ObjectId(session_id)})
    await api.revoke_token(token)

    return response