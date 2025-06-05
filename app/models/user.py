from bson import ObjectId
from datetime import datetime, UTC
import bcrypt
from app.models.database import users

class User:
    @staticmethod
    def find_by_id(user_id):
        """Find a user by ID"""
        return users.find_one({"_id": ObjectId(user_id)})

    @staticmethod
    def find_all_except(user_id):
        """Find all users except the specified one"""
        return users.find({"_id": {"$ne": ObjectId(user_id)}})


    @staticmethod
    def search_users(query, exclude_user_id=None, projection=None):
        """Search users by name or username, excluding a specific user"""
        filter_query = {
            "$or": [
                {"nom": {"$regex": query, "$options": "i"}},
                {"prenom": {"$regex": query, "$options": "i"}},
                {"username": {"$regex": query, "$options": "i"}}
            ]
        }

        if exclude_user_id:
            filter_query["_id"] = {"$ne": ObjectId(exclude_user_id)}

        return users.find(filter_query, projection)
    
    @staticmethod
    def find_by_email(email):
        """Find a user by email"""
        return users.find_one({"email": email})
    
    @staticmethod
    def find_by_username(username):
        """Find a user by username"""
        return users.find_one({"username": username})
    
    @staticmethod
    def create(nom, prenom, username, email, password):
        """Create a new user"""
        # Hash the password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user document
        user_data = {
            "nom": nom,
            "prenom": prenom,
            "username": username,
            "email": email,
            "password": password_hash,
            "is_admin": False,
            "created_at": datetime.now(UTC)
        }
        
        # Insert into database
        result = users.insert_one(user_data)
        return result.inserted_id
    
    @staticmethod
    def update(user_id, data):
        """Update user information"""
        updates = {k: v for k, v in data.items() if k != '_id'}
        if 'updated_at' not in updates:
            updates['updated_at'] = datetime.now(UTC)
        
        users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
        return True
    
    @staticmethod
    def check_password(user, password):
        """Check if the password is correct"""
        return bcrypt.checkpw(password.encode('utf-8'), user['password'])
    
    @staticmethod
    def hash_password(password):
        """Hash a password"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())