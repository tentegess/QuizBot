import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import asyncio

load_dotenv()
uri = os.environ.get('DB_CONNECTION_STRING')

client = AsyncIOMotorClient(uri)
client.get_io_loop = asyncio.get_event_loop

db = client.Quizbot
session_collection = db['Sessions']
quiz_collection = db['Quizzes']
user_collection = db['Users']
game_collection = db['Games']
answer_collection = db['Answers']
result_collection = db['Results']

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect: {e}")

