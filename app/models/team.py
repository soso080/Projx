from bson import ObjectId
from datetime import datetime, UTC
from app.models.database import teams, projects
from app.models.team_member import TeamMember

class Team:
    @staticmethod
    def find_by_id(team_id):
        """Find a team by ID"""
        return teams.find_one({"_id": ObjectId(team_id)})

    @staticmethod
    def find_by_member(user_id):
        """Find all teams where the user is a member"""
        # Get all team memberships for this user
        memberships = TeamMember.find_by_user(user_id)
        team_ids = [membership['team_id'] for membership in memberships]

        # If no memberships, return empty list
        if not team_ids:
            return []

        # Find all teams with these IDs
        return teams.find({"_id": {"$in": team_ids}})

    @staticmethod
    def create(name, description, creator_id, members=None):
        """Create a new team"""
        if members is None:
            members = []

        # Create team document (without members field)
        team_data = {
            "name": name,
            "description": description,
            "created_by": ObjectId(creator_id),
            "chef": ObjectId(creator_id),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        # Insert into database
        result = teams.insert_one(team_data)
        team_id = result.inserted_id

        # Add creator as leader
        TeamMember.add_member(team_id, creator_id, role="leader")

        # Add other members
        for member_id in members:
            if member_id != creator_id:  # Skip creator as they're already added
                TeamMember.add_member(team_id, member_id)

        return team_id

    @staticmethod
    def update(team_id, data):
        """Update team information"""
        updates = {k: v for k, v in data.items() if k not in ['_id', 'members']}
        if 'updated_at' not in updates:
            updates['updated_at'] = datetime.now(UTC)

        # Update team document
        teams.update_one({"_id": ObjectId(team_id)}, {"$set": updates})

        # Handle members separately if provided
        if 'members' in data:
            # Get current members
            current_memberships = list(TeamMember.find_by_team(team_id))
            current_member_ids = [str(membership['user_id']) for membership in current_memberships]

            # Determine members to add and remove
            new_member_ids = [member_id for member_id in data['members']]
            members_to_add = [m for m in new_member_ids if m not in current_member_ids]
            members_to_remove = [m for m in current_member_ids if m not in new_member_ids]

            # Add new members
            for member_id in members_to_add:
                TeamMember.add_member(team_id, member_id)

            # Remove members no longer in the list
            for member_id in members_to_remove:
                # Don't remove the team leader
                if data.get('chef') != member_id:
                    TeamMember.remove_member(team_id, member_id)

        return True

    @staticmethod
    def delete(team_id):
        """Delete a team and its projects"""
        # Delete the team
        result = teams.delete_one({"_id": ObjectId(team_id)})

        if result.deleted_count == 1:
            # Delete all team memberships
            TeamMember.delete_team_memberships(team_id)

            # Delete all projects associated with this team
            projects.delete_many({"team_id": ObjectId(team_id)})
            return True
        return False

    @staticmethod
    def add_member(team_id, user_id):
        """Add a member to the team"""
        return TeamMember.add_member(team_id, user_id)

    @staticmethod
    def remove_member(team_id, user_id):
        """Remove a member from the team"""
        return TeamMember.remove_member(team_id, user_id)

    @staticmethod
    def get_members(team_id):
        """Get all members of a team"""
        return TeamMember.find_by_team(team_id)
