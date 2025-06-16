from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# MongoDB connection
client_db = MongoClient(DATABASE_URL)
projx_db = client_db["projx"]

# Collections
users = projx_db["users"]
teams = projx_db["teams"]
team_members = projx_db["team_members"]
tasks = projx_db["tasks"]
projects = projx_db["projects"]
notifications = projx_db["notifications"]
project_comments = projx_db["project_comments"]  # New collection for project comments
contacts = projx_db["contacts"]

def init_db(app):
    # This function can be used to initialize the database
    # or perform any setup needed when the app starts
    app.logger.info("Database initialized")
