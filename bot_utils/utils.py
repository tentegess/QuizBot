from discord import Interaction, app_commands
import logging

from model.quiz_model import QuizModel


def guild_only():
    def predicate(interaction: Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.CheckFailure("Ta komenda nie jest dostępna w DM.")
        return True
    return app_commands.check(predicate)

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
    if anslen < 10:
            return i // 4
    elif anslen < 30:
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