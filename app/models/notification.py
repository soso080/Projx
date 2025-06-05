from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import notifications

class Notification:
    @staticmethod
    def find_by_id(notification_id):
        """Find a notification by ID"""
        return notifications.find_one({"_id": ObjectId(notification_id)})
    
    @staticmethod
    def find_by_user(user_id, unread_only=False, limit=50):
        """Find notifications for a user"""
        query = {"user_id": ObjectId(user_id)}
        if unread_only:
            query["read"] = False
        
        return notifications.find(query).sort("created_at", -1).limit(limit)
    
    @staticmethod
    def create(user_id, message, notification_type, sender_id=None, project_id=None, task_id=None):
        """Create a new notification"""
        notification_data = {
            "user_id": ObjectId(user_id),
            "message": message,
            "type": notification_type,
            "read": False,
            "created_at": datetime.now(UTC)
        }
        
        if sender_id:
            notification_data["sender_id"] = ObjectId(sender_id)
        if project_id:
            notification_data["project_id"] = ObjectId(project_id)
        if task_id:
            notification_data["task_id"] = ObjectId(task_id)
        
        result = notifications.insert_one(notification_data)
        return result.inserted_id
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark a notification as read"""
        result = notifications.update_one(
            {"_id": ObjectId(notification_id), "user_id": ObjectId(user_id)},
            {"$set": {"read": True, "read_at": datetime.now(UTC)}}
        )
        return result.modified_count == 1
    
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications for a user as read"""
        result = notifications.update_many(
            {"user_id": ObjectId(user_id), "read": False},
            {"$set": {"read": True, "read_at": datetime.now(UTC)}}
        )
        return result.modified_count
    
    @staticmethod
    def count_unread(user_id):
        """Count unread notifications for a user"""
        return notifications.count_documents({"user_id": ObjectId(user_id), "read": False})