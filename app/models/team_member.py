from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import team_members, teams

class TeamMember:
    @staticmethod
    def find_by_team(team_id):
        """Find all members of a team"""
        return team_members.find({"team_id": ObjectId(team_id)})
    
    @staticmethod
    def find_by_user(user_id):
        """Find all teams a user is a member of"""
        return team_members.find({"user_id": ObjectId(user_id)})
    
    @staticmethod
    def find_one(team_id, user_id):
        """Find a specific team membership"""
        return team_members.find_one({
            "team_id": ObjectId(team_id),
            "user_id": ObjectId(user_id)
        })
    
    @staticmethod
    def add_member(team_id, user_id, role="member"):
        """Add a user to a team"""
        # Check if the membership already exists
        existing = TeamMember.find_one(team_id, user_id)
        if existing:
            return False
        
        # Create new membership
        member_data = {
            "team_id": ObjectId(team_id),
            "user_id": ObjectId(user_id),
            "role": role,
            "joined_at": datetime.now(UTC)
        }
        
        result = team_members.insert_one(member_data)
        return result.inserted_id
    
    @staticmethod
    def remove_member(team_id, user_id):
        """Remove a user from a team"""
        result = team_members.delete_one({
            "team_id": ObjectId(team_id),
            "user_id": ObjectId(user_id)
        })
        return result.deleted_count > 0
    
    @staticmethod
    def update_role(team_id, user_id, role):
        """Update a member's role in a team"""
        result = team_members.update_one(
            {
                "team_id": ObjectId(team_id),
                "user_id": ObjectId(user_id)
            },
            {
                "$set": {"role": role}
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def is_member(team_id, user_id):
        """Check if a user is a member of a team"""
        return TeamMember.find_one(team_id, user_id) is not None
    
    @staticmethod
    def get_team_members_count(team_id):
        """Get the number of members in a team"""
        return team_members.count_documents({"team_id": ObjectId(team_id)})
    
    @staticmethod
    def delete_team_memberships(team_id):
        """Delete all memberships for a team (when deleting a team)"""
        result = team_members.delete_many({"team_id": ObjectId(team_id)})
        return result.deleted_count