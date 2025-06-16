from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import projects, tasks, project_comments

class Project:
    @staticmethod
    def find_by_id(project_id):
        """Find a project by ID"""
        return projects.find_one({"_id": ObjectId(project_id)})

    @staticmethod
    def find_by_team(team_id):
        """Find all projects for a team"""
        return projects.find({"team_id": ObjectId(team_id)})

    @staticmethod
    def create(name, description, team_id, creator_id, start_date=None, end_date=None, status="active"):
        """Create a new project"""
        # Create project document
        project_data = {
            "name": name,
            "description": description,
            "team_id": ObjectId(team_id),
            "created_by": ObjectId(creator_id),
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "tasks": [],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        # Insert into database
        result = projects.insert_one(project_data)
        return result.inserted_id

    @staticmethod
    def update(project_id, data):
        """Update project information"""
        updates = {k: v for k, v in data.items() if k != '_id'}
        if 'updated_at' not in updates:
            updates['updated_at'] = datetime.now(UTC)

        # Handle ObjectId fields
        if 'team_id' in updates:
            updates['team_id'] = ObjectId(updates['team_id'])

        projects.update_one({"_id": ObjectId(project_id)}, {"$set": updates})
        return True

    @staticmethod
    def delete(project_id):
        """Delete a project and its tasks"""
        # Get the project to find its tasks
        project = projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return False

        # Delete the project
        result = projects.delete_one({"_id": ObjectId(project_id)})

        # Delete all tasks associated with this project
        if result.deleted_count == 1:
            tasks.delete_many({"project_id": ObjectId(project_id)})
            return True
        return False

    @staticmethod
    def add_task(project_id, task_id):
        """Add a task to the project"""
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$push": {"tasks": ObjectId(task_id)}}
        )
        return True

    @staticmethod
    def remove_task(project_id, task_id):
        """Remove a task from the project"""
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$pull": {"tasks": ObjectId(task_id)}}
        )
        return True

    @staticmethod
    def add_comment(project_id, user_id, content):
        """Add a comment to a project"""
        comment_data = {
            "project_id": ObjectId(project_id),
            "user_id": ObjectId(user_id),
            "content": content,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        result = project_comments.insert_one(comment_data)
        return result.inserted_id

    @staticmethod
    def get_comments(project_id):
        """Get all comments for a project"""
        return project_comments.find({"project_id": ObjectId(project_id)}).sort("created_at", 1)

    @staticmethod
    def delete_comments(project_id):
        """Delete all comments for a project"""
        project_comments.delete_many({"project_id": ObjectId(project_id)})
