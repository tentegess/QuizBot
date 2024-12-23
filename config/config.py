import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()
uri = os.environ.get('DB_CONNECTION_STRING')

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

db = client.Quizbot
session_collection = db['Sessions']

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)