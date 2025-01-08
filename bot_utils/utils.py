from enum import Enum

from discord import Interaction, app_commands
import logging

from pymongo import DESCENDING, ASCENDING

from model.quiz_model import QuizModel

async def get_quiz(db,access_code):
    doc = await db["Quizzes"].find_one({"access_code": access_code})
    if not doc:
        return None
    return QuizModel(**doc)

def set_logger():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter(fmt="[{asctime}] [{levelname:<8}] {name}: {message}", datefmt="%Y-%m-%d %H:%M:%S",
                                      style="{")

    file_handler = logging.FileHandler(filename="./discord.log", encoding="utf-8", mode='w')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    return logger, console_handler

def get_row(anslen, i):
    if anslen <= 70:
            return i // 5
    elif anslen <= 100:
            return i // 3
    elif anslen <= 180:
            return i // 2
    else:
            return i



def calc_shards(inst_index, total_inst, total_shards):
    if total_inst > total_shards:
        raise ValueError(f"Error: Liczba instancji ({total_inst}) nie może przekraczać liczby shardów ({total_shards}).")

    if inst_index >= total_inst:
        raise ValueError(f"Error: Przekroczono liczbę zadeklarowanych instancji: {total_inst}.")

    if total_inst == total_shards:
        start_shard = inst_index
        end_shard = inst_index
    else:
        base_shards_per_instance = total_shards // total_inst
        extra_shards = total_shards % total_inst

        if inst_index < extra_shards:
            start_shard = inst_index * (base_shards_per_instance + 1)
            end_shard = start_shard + base_shards_per_instance
        else:
            start_shard = inst_index * base_shards_per_instance + extra_shards
            end_shard = start_shard + base_shards_per_instance - 1

    shard_ids = list(range(start_shard, end_shard + 1))
    if not shard_ids:
        raise ValueError(
             f"Error: Instancja {inst_index} nie ma przypisanych shardów.")
    return shard_ids

async def count_quizzes(db, user_id: int, search: str) -> int:
    filters = {
        "$or": [
            {"is_private": False},
            {"is_private": True, "user_id": user_id}
        ],
        "title": {"$regex": search, "$options": "i"}
    }
    total = await db["Quizzes"].count_documents(filters)
    return total


async def fetch_quizzes_page(
    db,
    user_id: int,
    search: str,
    page: int,
    page_size: int,
    sort,
) :
    match sort:
        case "title_asc":
            sort_order = [("title_lower", 1)]
        case "title_desc":
            sort_order = [("title_lower", -1)]
        case "question_asc":
            sort_order = [("questions", 1)]
        case "question_desc":
            sort_order = [("questions", -1)]
        case "author_asc":
            sort_order = [("author_lower", 1)]
        case "author_desc":
            sort_order = [("author_lower", -1)]
        case "created_asc":
            sort_order = [("created_at", 1)]
        case "created_desc":
            sort_order = [("created_at", -1)]
        case "updated_asc":
            sort_order = [("updated_at", 1)]
        case "updated_desc":
            sort_order = [("updated_at", -1)]
        case _:
            sort_order = [("created_at", -1)]

    filters = {
        "$or": [
            {"is_private": False},
            {"is_private": True, "user_id": user_id}
        ],
        "title": {"$regex": search, "$options": "i"}
    }

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
                "access_code":1,
                "author_lower": {"$toLower": "$author"},
                "title_lower": {"$toLower": "$title"}
            }
        },
        {
            "$sort": dict(sort_order)
        },
        {"$skip": page * page_size},
        {"$limit": page_size}
    ]

    docs = await db["Quizzes"].aggregate(pipeline).to_list()

    results = []
    for doc in docs:
        title = doc.get("title", "")
        questions_count = doc.get("questions", 0)
        user_id_ = doc.get("author")
        acode = doc.get("access_code")
        updated_at = doc.get("updated_at").isoformat(" ", "seconds")

        results.append({
            "title": title,
            "questions_count": questions_count,
            "user_id": user_id_,
            "access_code": acode,
            "updated_at": updated_at
        })

    return results

