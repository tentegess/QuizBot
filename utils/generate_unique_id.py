import random
import string
from config.config import quiz_collection

async def get_unique_access_code():
    while True:
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        existing_quiz = await quiz_collection.find_one({'access_code': code})
        if not existing_quiz:
            return code