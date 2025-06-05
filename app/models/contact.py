from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import contacts

class Contact:
    @staticmethod
    def find_by_id(contact_id):
        """Find a contact message by ID"""
        return contacts.find_one({"_id": ObjectId(contact_id)})
    
    @staticmethod
    def find_all(page=1, per_page=10, filter_type=None):
        """Find all contact messages with pagination"""
        query = {}
        if filter_type and filter_type != 'all':
            query = {"subject": filter_type}
        
        total = contacts.count_documents(query)
        
        messages = list(contacts.find(query)
                        .sort("created_at", -1)
                        .skip((page - 1) * per_page)
                        .limit(per_page))
        
        return {
            "messages": messages,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    
    @staticmethod
    def create(name, email, subject, message):
        """Create a new contact message"""
        contact_data = {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "created_at": datetime.now(UTC)
        }
        
        result = contacts.insert_one(contact_data)
        return result.inserted_id
    
    @staticmethod
    def delete(contact_id):
        """Delete a contact message"""
        result = contacts.delete_one({"_id": ObjectId(contact_id)})
        return result.deleted_count == 1