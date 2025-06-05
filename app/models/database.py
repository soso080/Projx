from pymongo import MongoClient

# MongoDB connection
client_db = MongoClient("mongodb+srv://soso:soso@cluster0.ggd13ry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
projx_db = client_db["projx"]

# Collections
users = projx_db["users"]
teams = projx_db["teams"]
tasks = projx_db["tasks"]
projects = projx_db["projects"]
notifications = projx_db["notifications"]
task_comments = projx_db["task_comments"]
sprints = projx_db["sprints"]
team_messages = projx_db["team_messages"]
contacts = projx_db["contacts"]
admin_collection = projx_db["admin"]

def init_db(app):
    # This function can be used to initialize the database
    # or perform any setup needed when the app starts
    app.logger.info("Database initialized")