import asyncio
from datetime import datetime, timedelta, timezone
from http.client import responses
import discord
from bson.objectid import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException, Cookie, status, File, UploadFile, Form, Response
from fastapi.params import Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from requests import session
from typing import List
from model.session_model import SessionModel
from model.quiz_model import QuizModel
from model.question_model import QuestionModel
from model.option_model import OptionModel
from model.user_model import UserModel
from utils.auth import Oauth, api
from utils.validate_session import validate_session_without_data, validate_session_with_data
from utils.validate_quiz import validate_quiz_data, img_scaling
from utils.generate_unique_id import get_unique_access_code
from discord.ext.ipc import Client
from config.config import session_collection, quiz_collection, db, user_collection
import json
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from math import ceil
from fastapi.responses import JSONResponse
from pymongo import ASCENDING, DESCENDING
from fastapi.responses import StreamingResponse
import pytz


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
        data: dict = Depends(validate_session_with_data),
        quiz_id: Optional[str] = Form(None)
):
    user = data['user']
    user_id = user.get("id")

    if quiz_id:
        quiz_id = ObjectId(quiz_id)
        quiz = await quiz_collection.find_one({"_id": quiz_id})
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if quiz["user_id"] != int(user_id):
            raise HTTPException(status_code=401, detail="brak uprawnień")

    questions_data = json.loads(questions)
    if not validate_quiz_data(title, questions_data):
        raise HTTPException(status_code=400, detail="Niepoprawnie uzupełnione dane.")

    saved_questions = []
    file_idx = 0
    fs = AsyncIOMotorGridFSBucket(db)

    for question in questions_data:
        image_url = question.get('image_url')
        if image_url and not image_url.startswith("file_"):
            image_url = ObjectId(image_url)
        elif image_url and image_url.startswith("file_"):
            image_file = files[file_idx]
            file_contents = await image_file.read()

            file_contents = img_scaling(file_contents)
            grid_file_id = await fs.upload_from_stream(image_file.filename, file_contents)
            image_url = grid_file_id
            file_idx += 1
        else:
            if question.get('image_url'):
                try:
                    await fs.delete(ObjectId(question['image_url']))
                except Exception as e:
                    print(f"Błąd podczas usuwania zdjęcia: {e}")
            image_url = None

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

    if quiz_id:
        saved_questions.append(saved_question.model_dump())
        await quiz_collection.update_one(
            {"_id": quiz_id},
            {"$set": {
                'title': title,
                'updated_at': datetime.now(timezone.utc),
                'questions': saved_questions
            }},
        )
    else:
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

@main_router.get("/quiz")
async def get_quizzes(request: Request, _: None = Depends(validate_session_without_data)):

    return templates.TemplateResponse(
        "show_quizzes.html",
        {
            "request": request,
        }
    )

@main_router.get("/quiz/data")
async def get_quizzes_data(page: int = 1, sort: str = "title_asc", search: str = "", data: dict = Depends(validate_session_with_data)):
    user = data['user']
    user_id = user.get("id")

    filters = {}
    if search:
        filters["title"] = {"$regex": search, "$options": "i"}

    sort_order = []
    collation = {"locale": "en", "strength": 1}

    if sort == "title_asc":
        sort_order = [("title", ASCENDING)]
    elif sort == "title_desc":
        sort_order = [("title", DESCENDING)]
    elif sort == "questions_asc":
        sort_order = [("questions", ASCENDING)]
    elif sort == "questions_desc":
        sort_order = [("questions", DESCENDING)]
    elif sort == "author_asc":
        sort_order = [("author", ASCENDING)]
    elif sort == "author_desc":
        sort_order = [("author", DESCENDING)]
    elif sort == "create_date_asc":
        sort_order = [("created_at", ASCENDING)]
    elif sort == "create_date_desc":
        sort_order = [("created_at", DESCENDING)]
    elif sort == "updated_date_asc":
        sort_order = [("updated_at", ASCENDING)]
    elif sort == "updated_date_desc":
        sort_order = [("updated_at", DESCENDING)]
    else:
        sort_order = [("updated_at", ASCENDING)]

    quizzes_cursor = quiz_collection.find(
        filters, {"title": 1, "author": 1, "questions": 1, "_id": 1, "user_id": 1, "created_at": 1, "updated_at": 1}
    ).sort(sort_order).collation(collation).skip((page - 1) * 9).limit(9)

    quizzes = []
    async for quiz in quizzes_cursor:
        is_editable = False
        if quiz["user_id"] == int(user_id):
            is_editable = True
        questions_count = len(quiz["questions"])

        user = await user_collection.find_one({"user_id": quiz["user_id"]}, {"username": 1})

        quizzes.append({
            "_id": str(quiz["_id"]),
            "title": quiz["title"],
            "author": user["username"],
            "questions": questions_count,
            "created_at": quiz["created_at"].isoformat(),
            "updated_at": quiz["updated_at"].isoformat(),
            "is_editable": is_editable
        })

    total_quizzes = await quiz_collection.count_documents(filters)
    total_pages = ceil(total_quizzes / 9)

    return JSONResponse({
        "quizzes": quizzes,
        "page": page,
        "total_pages": total_pages
    })

@main_router.delete("/quiz/delete/{quiz_id}")
async def delete_quiz(quiz_id: str, data: dict = Depends(validate_session_with_data)):
    user = data['user']
    user_id = user.get("id")
    quiz_object_id = ObjectId(quiz_id)

    quiz = await quiz_collection.find_one({"_id": quiz_object_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if quiz["user_id"] != int(user_id):
        raise HTTPException(status_code=401, detail="brak uprawnień")

    await quiz_collection.delete_one({"_id": quiz_object_id})

    return Response(status_code=204)

@main_router.get("/quiz/edit/{quiz_id}")
async def get_quiz(request: Request, quiz_id: str, data: dict = Depends(validate_session_with_data)):
    try:
        user = data['user']
        user_id = user.get("id")
        quiz = await quiz_collection.find_one(
            {"_id": ObjectId(quiz_id)},
            {"access_code": 0, "created_at": 0, "updated_at": 0}
        )

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if quiz["user_id"] != int(user_id):
            raise HTTPException(status_code=401, detail="brak uprawnień")

        quiz["_id"] = str(quiz["_id"])
        for question in quiz["questions"]:
            question["image_url"] = f"/quiz/image/{str(question.get('image_url'))}" if question.get('image_url') else None

        return templates.TemplateResponse(
            "edit_quiz.html",
            {
                "request": request,
                "quiz": quiz
            })
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=404, detail="Quiz not found")

@main_router.get("/quiz/image/{img_id}")
async def get_image(img_id: str):
    try:
        fs = AsyncIOMotorGridFSBucket(db)
        file_data = await fs.open_download_stream(ObjectId(img_id))
        return StreamingResponse(file_data, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image not found: {str(e)}")

@main_router.get("/quiz/view/{quiz_id}")
async def view_quiz(request: Request, quiz_id: str, data: dict = Depends(validate_session_with_data)):
    user = data['user']
    user_id = int(user.get("id"))
    user = await user_collection.find_one({"user_id": user_id}, {"username": 1})

    try:
        quiz = await quiz_collection.find_one(
            {"_id": ObjectId(quiz_id)}
        )

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        quiz["_id"] = str(quiz["_id"])
        time_zone = pytz.timezone('Europe/Warsaw')
        quiz['created_at'] = pytz.utc.localize(quiz['created_at']).astimezone(time_zone).strftime('%d-%m-%Y %H:%M:%S')
        quiz['updated_at'] = pytz.utc.localize(quiz['updated_at']).astimezone(time_zone).strftime('%d-%m-%Y %H:%M:%S')

        for question in quiz["questions"]:
            question["image_url"] = f"/quiz/image/{str(question.get('image_url'))}" if question.get('image_url') else None

        return templates.TemplateResponse(
            "view_quiz.html",
            {
                "request": request,
                "quiz": quiz,
                "author": user["username"]
            })
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=404, detail="Quiz not found")

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