from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import tasks, project_comments as task_comments

class Task:
    @staticmethod
    def find_by_id(task_id):
        """Find a task by ID"""
        return tasks.find_one({"_id": ObjectId(task_id)})
    
    @staticmethod
    def find_by_project(project_id):
        """Find all tasks for a project"""
        return tasks.find({"project_id": ObjectId(project_id)})
    
    @staticmethod
    def find_by_assigned_to(user_id):
        """Find all tasks assigned to a user"""
        return tasks.find({"assigned_to": ObjectId(user_id)})
    
    @staticmethod
    def create(title, project_id, assigned_to, creator_id, description="", due_date=None, status="todo"):
        """Create a new task"""
        # Create task document
        task_data = {
            "title": title,
            "description": description,
            "project_id": ObjectId(project_id),
            "assigned_to": ObjectId(assigned_to),
            "created_by": ObjectId(creator_id),
            "due_date": due_date,
            "status": status,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        # Insert into database
        result = tasks.insert_one(task_data)
        return result.inserted_id
    
    @staticmethod
    def update(task_id, data):
        """Update task information"""
        updates = {k: v for k, v in data.items() if k != '_id'}
        if 'updated_at' not in updates:
            updates['updated_at'] = datetime.now(UTC)
        
        # Handle ObjectId fields
        if 'project_id' in updates:
            updates['project_id'] = ObjectId(updates['project_id'])
        if 'assigned_to' in updates:
            updates['assigned_to'] = ObjectId(updates['assigned_to'])
        
        tasks.update_one({"_id": ObjectId(task_id)}, {"$set": updates})
        return True
    
    @staticmethod
    def delete(task_id):
        """Delete a task and its comments"""
        # Delete the task
        result = tasks.delete_one({"_id": ObjectId(task_id)})
        
        # Delete all comments associated with this task
        if result.deleted_count == 1:
            task_comments.delete_many({"task_id": ObjectId(task_id)})
            return True
        return False
    
    @staticmethod
    def add_comment(task_id, user_id, content):
        """Add a comment to a task"""
        comment_data = {
            "task_id": ObjectId(task_id),
            "user_id": ObjectId(user_id),
            "content": content,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        result = task_comments.insert_one(comment_data)
        return result.inserted_id
    
    @staticmethod
    def get_comments(task_id):
        """Get all comments for a task"""
        return task_comments.find({"task_id": ObjectId(task_id)}).sort("created_at", 1)