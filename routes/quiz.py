from datetime import datetime, timezone
from bson.objectid import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form, Response
from fastapi.params import Depends
from fastapi.templating import Jinja2Templates
from model.quiz_model import QuizModel
from model.question_model import QuestionModel
from model.option_model import OptionModel
from utils.auth import api
from utils.validate_session import validate_session_without_data, validate_session_with_data
from utils.validate_quiz import validate_quiz_data, img_scaling
from utils.generate_unique_id import get_unique_access_code
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
quiz_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@quiz_router.get("/new-quiz")
async def make_quiz(request: Request, _: None = Depends(validate_session_without_data)):
    return templates.TemplateResponse(
        "make_quiz.html",
        {
            "request": request,
        })

@quiz_router.post("/quiz/add")
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
        quiz = await quiz_collection.find_one({"_id": quiz_id, "is_active": True})
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
        else:
            saved_questions.append(saved_question)

    if quiz_id:
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

@quiz_router.get("/quiz")
async def get_quizzes(request: Request, _: None = Depends(validate_session_without_data)):

    return templates.TemplateResponse(
        "show_quizzes.html",
        {
            "is_only_my_quiz": False,
            "is_user_logged": True,
            "request": request,
        }
    )

@quiz_router.get("/quiz/my")
async def get_my_quizzes(request: Request, _: None = Depends(validate_session_without_data)):

    return templates.TemplateResponse(
        "show_quizzes.html",
        {
            "is_only_my_quiz": True,
            "is_user_logged": True,
            "request": request,
        }
    )

@quiz_router.get("/quiz/all")
async def get_all_quizzes(request: Request):

    return templates.TemplateResponse(
        "show_quizzes.html",
        {
            "is_only_my_quiz": False,
            "is_user_logged": False,
            "request": request,
            "is_not_logged": True,
        }
    )

@quiz_router.get("/quiz/data")
async def get_quizzes_data(
    request: Request,
    page: int = 1,
    sort: str = "title_asc",
    search: str = "",
    is_only_my_quiz: bool = False,
    is_user_logged: bool = True,
):
    if is_user_logged:
        data = await validate_session_with_data(request)
        user = data['user']
        user_id = int(user.get("id"))

    if is_only_my_quiz:
        filters = {"user_id": user_id}
    elif not is_user_logged:
        filters = {"is_private": False}
    else:
        filters = {
            "$or": [
                {"is_private": False},
                {"is_private": True, "user_id": user_id}
            ]
        }

    filters["is_active"] = True
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
        if is_user_logged:
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

@quiz_router.delete("/quiz/delete/{quiz_id}")
async def delete_quiz(quiz_id: str, data: dict = Depends(validate_session_with_data)):
    user = data['user']
    user_id = user.get("id")
    quiz_object_id = ObjectId(quiz_id)

    quiz = await quiz_collection.find_one({"_id": quiz_object_id, "is_active": True})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz nie istnieje")
    if quiz["user_id"] != int(user_id):
        raise HTTPException(status_code=401, detail="Brak uprawnień")

    await quiz_collection.update_one({"_id": quiz_object_id}, {"$set": {"is_active": False}})

    return Response(status_code=204)

@quiz_router.get("/quiz/edit/{quiz_id}")
async def get_quiz(request: Request, quiz_id: str, data: dict = Depends(validate_session_with_data)):
    try:
        user = data['user']
        user_id = user.get("id")
        quiz = await quiz_collection.find_one(
            {"_id": ObjectId(quiz_id), "is_active": True},
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

@quiz_router.get("/quiz/image/{img_id}")
async def get_image(img_id: str):
    try:
        fs = AsyncIOMotorGridFSBucket(db)
        file_data = await fs.open_download_stream(ObjectId(img_id))
        return StreamingResponse(file_data, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Zdjęcie nie istnieje: {str(e)}")

@quiz_router.get("/quiz/view/{quiz_id}")
async def view_quiz(request: Request, quiz_id: str):
    session_id = request.cookies.get("session_id")
    session = await session_collection.find_one({"_id": ObjectId(session_id)})

    if session:
        token = session.get("token")
        user = await api.get_user(token)
        user_id = int(user.get("id"))
    else:
        user_id = None

    try:
        quiz = await quiz_collection.find_one({"_id": ObjectId(quiz_id), "is_active": True})

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

        if user_id:
            return templates.TemplateResponse(
                "view_quiz.html",
                {
                    "request": request,
                    "quiz": quiz,
                    "author": user["username"],
                    "game_count": game_count
                })
        else:
            return templates.TemplateResponse(
                "view_quiz.html",
                {
                    "request": request,
                    "quiz": quiz,
                    "author": user["username"],
                    "game_count": game_count,
                    "is_not_logged": True
                })
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=404, detail="Quiz nie istnieje")