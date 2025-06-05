from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import teams, projects

class Team:
    @staticmethod
    def find_by_id(team_id):
        """Find a team by ID"""
        return teams.find_one({"_id": ObjectId(team_id)})
    
    @staticmethod
    def find_by_member(user_id):
        """Find all teams where the user is a member"""
        return teams.find({"members": ObjectId(user_id)})
    
    @staticmethod
    def create(name, description, creator_id, members=None):
        """Create a new team"""
        if members is None:
            members = []
        
        # Always add the creator as a member
        if creator_id not in members:
            members.append(creator_id)
        
        # Create team document
        team_data = {
            "name": name,
            "description": description,
            "created_by": ObjectId(creator_id),
            "chef": ObjectId(creator_id),
            "members": [ObjectId(member) for member in members],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        # Insert into database
        result = teams.insert_one(team_data)
        return result.inserted_id
    
    @staticmethod
    def update(team_id, data):
        """Update team information"""
        updates = {k: v for k, v in data.items() if k != '_id'}
        if 'updated_at' not in updates:
            updates['updated_at'] = datetime.now(UTC)
        
        # Handle members separately if provided
        if 'members' in updates:
            updates['members'] = [ObjectId(member) for member in updates['members']]
        
        teams.update_one({"_id": ObjectId(team_id)}, {"$set": updates})
        return True
    
    @staticmethod
    def delete(team_id):
        """Delete a team and its projects"""
        # Delete the team
        result = teams.delete_one({"_id": ObjectId(team_id)})
        
        # Delete all projects associated with this team
        if result.deleted_count == 1:
            projects.delete_many({"team_id": ObjectId(team_id)})
            return True
        return False
    
    @staticmethod
    def add_member(team_id, user_id):
        """Add a member to the team"""
        teams.update_one(
            {"_id": ObjectId(team_id)},
            {"$addToSet": {"members": ObjectId(user_id)}}
        )
        return True
    
    @staticmethod
    def remove_member(team_id, user_id):
        """Remove a member from the team"""
        teams.update_one(
            {"_id": ObjectId(team_id)},
            {"$pull": {"members": ObjectId(user_id)}}
        )
        return True