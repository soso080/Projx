from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from bson import ObjectId
import json
from datetime import datetime, UTC

from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User

# Create a blueprint for the team routes
team_bp = Blueprint('team', __name__)

@team_bp.route('/team')
def team():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    # Récupère toutes les équipes où l'utilisateur est membre
    user_teams = Team.find_by_member(session['user_id'])
    teams_list = list(user_teams)

    # Préparer les données complètes des équipes
    teams_with_details = []
    for team in teams_list:
        team_dict = dict(team)

        # Récupérer le chef d'équipe
        leader = User.find_by_id(team['chef'])
        team_dict['leader'] = {
            'prenom': leader['prenom'],
            'nom': leader['nom'],
            'username': leader['username']
        }

        # Récupérer les infos de tous les membres
        team_dict['members_details'] = []

        # Get team memberships
        memberships = list(TeamMember.find_by_team(team['_id']))

        # Create a members list for backward compatibility
        team_dict['members'] = [membership['user_id'] for membership in memberships]

        # Get member details
        for membership in memberships:
            member = User.find_by_id(membership['user_id'])
            if member:
                team_dict['members_details'].append({
                    '_id': str(member['_id']),
                    'prenom': member['prenom'],
                    'nom': member['nom'],
                    'username': member['username']
                })

        teams_with_details.append(team_dict)

    return render_template("team.html",
                           teams=teams_with_details,
                           User=User)  # Passez la classe User au template

@team_bp.route('/edit_team/<team_id>')
def edit_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    team = Team.find_by_id(team_id)

    if not team:
        flash("Équipe non trouvée", 'error')
        return redirect(url_for('team.team'))

    # Récupérer les détails des membres
    member_details = []

    # Get team memberships
    memberships = list(TeamMember.find_by_team(team['_id']))

    # Add members list for backward compatibility
    team['members'] = [membership['user_id'] for membership in memberships]

    # Get member details
    for membership in memberships:
        user = User.find_by_id(membership['user_id'])
        if user:
            member_details.append(user)

    return render_template("edit_team.html",
                           team=team,
                           member_details=member_details)

@team_bp.route('/create_team', methods=['POST'])
def create_team():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    try:
        # 1. Gérer le cas où aucun membre n'est sélectionné
        members_json = request.form.get('members', '[]')  # '[]' par défaut si vide
        members = json.loads(members_json) if members_json else []  # Liste vide si JSON invalide

        # 2. Toujours ajouter le créateur comme membre
        creator_id = session['user_id']
        if creator_id not in members:
            members.append(creator_id)

        # 3. Validation - Au moins le créateur doit être membre
        if not members:
            flash("L'équipe doit avoir au moins un membre (vous)", 'error')
            return redirect(url_for('team.team'))

        # 4. Création de l'équipe
        name = request.form.get('name').strip()
        description = request.form.get('description', '').strip()

        # Validation supplémentaire
        if not name:
            flash("Le nom de l'équipe est obligatoire", 'error')
            return redirect(url_for('team.team'))

        Team.create(name, description, creator_id, members)
        flash('Équipe créée avec succès!', 'success')
        return redirect(url_for('team.team'))

    except Exception as e:
        flash("Erreur technique lors de la création", 'error')
        return redirect(url_for('team.team'))


@team_bp.route('/search_users')
def search_users():
    if 'user_id' not in session:
        return jsonify([])

    query = request.args.get('q', '').lower()
    if len(query) < 2:
        return jsonify([])

    # Recherche dans nom, prénom ou username
    users_list = list(User.search_users(
        query=query,
        exclude_user_id=session['user_id'],
        projection={"nom": 1, "prenom": 1, "username": 1}
    ))

    # Convertir ObjectId en string pour JSON
    for user in users_list:
        user['_id'] = str(user['_id'])

    return jsonify(users_list)

@team_bp.route('/update_team/<team_id>', methods=['PUT'])
def update_team(team_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # 1. Vérifier que l'équipe existe et que l'utilisateur est autorisé
        team = Team.find_by_id(team_id)
        if not team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        # Seul le créateur ou le chef peut modifier l'équipe
        creator_id = team.get("created_by")
        current_leader_id = team.get("chef")
        user_id = ObjectId(session['user_id'])

        if user_id not in [creator_id, current_leader_id]:
            return jsonify({"error": "Action non autorisée"}), 403

        # 2. Récupérer les données du formulaire
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données manquantes"}), 400

        # 3. Préparer les mises à jour
        updates = {
            "name": data.get("name", team["name"]).strip(),
            "description": data.get("description", team.get("description", "")).strip(),
            "chef": ObjectId(data.get("chef", team["chef"])),
            "updated_at": datetime.now(UTC)
        }

        # Validation du nom
        if not updates["name"]:
            return jsonify({"error": "Le nom de l'équipe est obligatoire"}), 400

        # 4. Gérer les membres (ajouts et suppressions)
        # Get current members from team_members collection
        memberships = list(TeamMember.find_by_team(team['_id']))
        current_members = set(str(membership['user_id']) for membership in memberships)

        members_to_remove = set(data.get("membersToRemove", []))
        new_members = set(data.get("newMembers", []))

        # Vérifier que le nouveau chef est toujours membre
        chef_id = str(updates["chef"])
        if chef_id not in (current_members - members_to_remove | new_members):
            return jsonify({"error": "Le chef doit être membre de l'équipe"}), 400

        # Update the chef's role to "leader"
        if chef_id != str(current_leader_id):
            TeamMember.update_role(team_id, chef_id, "leader")
            # If the previous leader is still a member, update their role to "member"
            if str(current_leader_id) in current_members and str(current_leader_id) not in members_to_remove:
                TeamMember.update_role(team_id, str(current_leader_id), "member")

        # 5. Appliquer les modifications dans MongoDB
        # Update team basic info
        Team.update(team_id, updates)

        # Add new members
        for member_id in new_members:
            if member_id not in current_members:
                role = "leader" if member_id == chef_id else "member"
                TeamMember.add_member(team_id, member_id, role)

        # Remove members
        for member_id in members_to_remove:
            if member_id in current_members and member_id != chef_id:  # Don't remove the chef
                TeamMember.remove_member(team_id, member_id)

        return jsonify({"success": True, "message": "Équipe mise à jour avec succès"})

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@team_bp.route('/delete_team/<team_id>', methods=['DELETE'])
def delete_team(team_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Vérifier que l'équipe existe
        team = Team.find_by_id(team_id)
        if not team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        # Seul le créateur peut supprimer l'équipe
        creator_id = team.get("created_by")
        user_id = ObjectId(session['user_id'])

        if user_id != creator_id:
            return jsonify({"error": "Action non autorisée"}), 403

        # Supprimer l'équipe
        if Team.delete(team_id):
            return jsonify({"success": True, "message": "Équipe supprimée avec succès"})
        else:
            return jsonify({"error": "Échec de la suppression"}), 500

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@team_bp.route('/get_team_details')
def get_team_details():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({"error": "ID d'équipe manquant"}), 400

    try:
        team = Team.find_by_id(team_id)
        if not team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        # Convertir ObjectId en string pour JSON
        team['_id'] = str(team['_id'])
        team['created_by'] = str(team['created_by'])
        team['chef'] = str(team['chef'])

        # Get team memberships
        memberships = list(TeamMember.find_by_team(team['_id']))

        # Create members list for backward compatibility
        member_ids = [str(membership['user_id']) for membership in memberships]

        # Récupérer les infos du chef
        leader = User.find_by_id(team['chef'])
        if leader:
            leader['_id'] = str(leader['_id'])
            team['leader'] = {
                '_id': leader['_id'],
                'nom': leader['nom'],
                'prenom': leader['prenom'],
                'username': leader['username']
            }

        # Récupérer les infos des membres
        members = []
        for membership in memberships:
            member_id = membership['user_id']
            member = User.find_by_id(member_id)
            if member:
                members.append({
                    '_id': str(member['_id']),
                    'nom': member['nom'],
                    'prenom': member['prenom'],
                    'username': member['username'],
                    'role': membership.get('role', 'member')
                })

        # Add members list to team
        team['members'] = members

        return jsonify(team)

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500
