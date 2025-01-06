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
from utils.discord_api import discord_api
from config.config import session_collection, quiz_collection, db, user_collection, game_collection
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
        "count": guild_count
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

@main_router.get("/guilds")
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
            guild["url"] = f"https://discord.com/oauth2/authorize?client_id=1308514751026036847&guild_id={guild['id']}"

        if guild.get("icon"):
            guild["icon"] = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}"
        else:
            guild["icon"] = "https://cdn.discordapp.com/embed/avatars/0.png"
        is_admin = discord.Permissions(int(guild["permissions"])).administrator

        if is_admin or guild["owner"]:
            perms.append(guild)

    perms *= 100

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

@main_router.get("/server/{guild_id}")
async def server(request: Request, guild_id: int, data: dict = Depends(validate_session_with_data)):
    session = data['session']
    user = data['user']
    token = session.get("token")

    stats = await discord_api.fetch_guild_name(guild_id)
    user_guilds = await api.get_guilds(token=session.get("token"))
    guild = next((g for g in user_guilds if g["id"] == str(guild_id)), None)

    if guild is None:
        return {"error": "Brak uprawnień"}

    is_admin = discord.Permissions(int(guild["permissions"])).administrator
    is_owner = guild["owner"]

    if not is_admin and not is_owner:
        return {"error": "Brak uprawnień"}

    return templates.TemplateResponse(
        "server.html",
        {
            "request": request,
            "name": stats["name"],
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
        quiz_id: Optional[str] = Form(None),
        is_private: bool = Form(False)
):
    user = data['user']
    user_id = user.get("id")

    if quiz_id:
        quiz_id = ObjectId(quiz_id)
        quiz = await quiz_collection.find_one({"_id": quiz_id})
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz nie istnieje")
        if quiz["user_id"] != int(user_id):
            raise HTTPException(status_code=401, detail="Brak uprawnień")

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
                    await fs.delete(ObjectId(question['image_url']))

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
                'questions': saved_questions,
                'is_private': is_private
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
            access_code=access_code,
            is_private = is_private
        )

        quiz_dict = quiz.model_dump()
        quiz_id = await quiz_collection.insert_one(quiz_dict)

    return JSONResponse(content={}, status_code=200)

@main_router.get("/quiz")
async def get_quizzes(request: Request, _: None = Depends(validate_session_without_data)):

    return templates.TemplateResponse(
        "show_quizzes.html",
        {
            "is_only_my_quiz": False,
            "request": request,
        }
    )

@main_router.get("/quiz/my")
async def get_my_quizzes(request: Request, _: None = Depends(validate_session_without_data)):

    return templates.TemplateResponse(
        "show_quizzes.html",
        {
            "is_only_my_quiz": True,
            "request": request,
        }
    )

@main_router.get("/quiz/data")
async def get_quizzes_data(
    page: int = 1,
    sort: str = "title_asc",
    search: str = "",
    is_only_my_quiz: bool = False,
    data: dict = Depends(validate_session_with_data)
):
    user = data['user']
    user_id = int(user.get("id"))

    if is_only_my_quiz:
        filters = {"user_id": user_id}
    else:
        filters = {
            "$or": [
                {"is_private": False},
                {"is_private": True, "user_id": user_id}
            ]
        }

    if search:
        filters["title"] = {"$regex": search, "$options": "i"}

    sort_order = []
    if sort == "title_asc":
        sort_order = [("title_lower", ASCENDING)]
    elif sort == "title_desc":
        sort_order = [("title_lower", DESCENDING)]
    elif sort == "questions_asc":
        sort_order = [("questions", ASCENDING)]
    elif sort == "questions_desc":
        sort_order = [("questions", DESCENDING)]
    elif sort == "author_asc":
        sort_order = [("author_lower", ASCENDING)]
    elif sort == "author_desc":
        sort_order = [("author_lower", DESCENDING)]
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

    pipeline = [
        {"$match": filters},
        {
            "$lookup": {
                "from": "Users",
                "localField": "user_id",
                "foreignField": "user_id",
                "as": "author_info"
            }
        },
        {
            "$addFields": {
                "author": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$author_info.username", 0]},
                        "Unknown Author"
                    ]
                },
                "questions": {"$size": "$questions"}
            }
        },
        {
            "$project": {
                "title": 1,
                "author": 1,
                "questions": 1,
                "created_at": 1,
                "updated_at": 1,
                "user_id": 1,
                "is_private": 1,
                "author_lower": {"$toLower": "$author"},
                "title_lower": {"$toLower": "$title"}
            }
        },
        {
            "$sort": dict(sort_order)
        },
        {"$skip": (page - 1) * 9},
        {"$limit": 9}
    ]

    quizzes_cursor = quiz_collection.aggregate(pipeline)

    quizzes = []
    async for quiz in quizzes_cursor:
        is_editable = False
        if quiz["user_id"] == user_id:
            is_editable = True

        quizzes.append({
            "_id": str(quiz["_id"]),
            "title": quiz["title"],
            "author": quiz["author"],
            "questions": quiz["questions"],
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
        raise HTTPException(status_code=404, detail="Quiz nie istnieje")
    if quiz["user_id"] != int(user_id):
        raise HTTPException(status_code=401, detail="Brak uprawnień")

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
            raise HTTPException(status_code=404, detail="Quiz nie istnieje")
        if quiz["user_id"] != int(user_id):
            raise HTTPException(status_code=401, detail="Brak uprawnień")

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
        raise HTTPException(status_code=404, detail="Quiz nie istnieje")

@main_router.get("/quiz/image/{img_id}")
async def get_image(img_id: str):
    try:
        fs = AsyncIOMotorGridFSBucket(db)
        file_data = await fs.open_download_stream(ObjectId(img_id))
        return StreamingResponse(file_data, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Zdjęcie nie istnieje: {str(e)}")

@main_router.get("/quiz/view/{quiz_id}")
async def view_quiz(request: Request, quiz_id: str, data: dict = Depends(validate_session_with_data)):
    user = data['user']
    user_id = int(user.get("id"))

    try:
        quiz = await quiz_collection.find_one(
            {"_id": ObjectId(quiz_id)}
        )

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz nie istnieje")
        if quiz["is_private"] and quiz["user_id"] != user_id:
            raise HTTPException(status_code=401, detail="Brak uprawnień")

        quiz["_id"] = str(quiz["_id"])
        time_zone = pytz.timezone('Europe/Warsaw')
        quiz['created_at'] = pytz.utc.localize(quiz['created_at']).astimezone(time_zone).strftime('%d-%m-%Y %H:%M:%S')
        quiz['updated_at'] = pytz.utc.localize(quiz['updated_at']).astimezone(time_zone).strftime('%d-%m-%Y %H:%M:%S')

        for question in quiz["questions"]:
            question["image_url"] = f"/quiz/image/{str(question.get('image_url'))}" if question.get('image_url') else None

        game_count = await game_collection.count_documents({"quiz_code": quiz["access_code"]})
        user = await user_collection.find_one({"user_id": quiz["user_id"]}, {"username": 1})

        return templates.TemplateResponse(
            "view_quiz.html",
            {
                "request": request,
                "quiz": quiz,
                "author": user["username"],
                "game_count": game_count
            })
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=404, detail="Quiz nie istnieje")

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
