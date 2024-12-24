import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
uri = os.environ.get('DB_CONNECTION_STRING')

# Create a new client and connect to the server
client = AsyncIOMotorClient(uri)
client.get_io_loop = asyncio.get_event_loop

db = client.Quizbot
session_collection = db['Sessions']
quiz_collection = db['Quizzes']
question_collection = db['Questions']
game_collection = db['Games']
answer_collection = db['Answers']

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)