from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from bson import ObjectId
from datetime import datetime, UTC

from app.models.project import Project
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User

# Create a blueprint for the project routes
project_bp = Blueprint('project', __name__)

@project_bp.route('/project')
def project():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    # Récupère les équipes de l'utilisateur
    user_teams = list(Team.find_by_member(session['user_id']))
    team_ids = [team['_id'] for team in user_teams]

    # Récupère les projets avec les détails complets des équipes
    user_projects = []
    for team_id in team_ids:
        projects = Project.find_by_team(team_id)
        for project in projects:
            # Ajoute les détails de l'équipe au projet
            project['team_details'] = next(
                (team for team in user_teams if team['_id'] == project['team_id']),
                None
            )
            user_projects.append(project)

    return render_template("project.html",
                           projects=user_projects,
                           teams=user_teams)

@project_bp.route('/edit_project/<project_id>')
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    project = Project.find_by_id(project_id)
    if not project:
        flash("Projet non trouvé", 'error')
        return redirect(url_for('project.project'))

    # Récupérer les équipes disponibles
    user_teams = list(Team.find_by_member(session['user_id']))

    return render_template("edit_project.html",
                         project=project,
                         teams=user_teams)

@project_bp.route('/create_project', methods=['POST'])
def create_project():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    try:
        # Récupérer les données du formulaire
        name = request.form.get('name').strip()
        description = request.form.get('description', '').strip()
        team_id = request.form.get('team_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status', 'active')

        # Validation ;;
        if not name or not team_id:
            flash('Le nom et l\'équipe sont obligatoires', 'error')
            return redirect(url_for('project.project'))

        # Convertir les dates
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        # Créer le projet
        Project.create(name, description, team_id, session['user_id'], start_date_obj, end_date_obj, status)
        flash('Projet créé avec succès!', 'success')
        return redirect(url_for('project.project'))

    except Exception as e:
        flash("Erreur technique lors de la création", 'error')
        return redirect(url_for('project.project'))

@project_bp.route('/get_project_details')
def get_project_details():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"error": "ID de projet manquant"}), 400

    try:
        project = Project.find_by_id(project_id)
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        # Convertir les champs ObjectId en strings
        project['_id'] = str(project['_id'])
        project['team_id'] = str(project['team_id'])
        project['created_by'] = str(project['created_by'])

        # Convertir les tâches si elles existent
        if 'tasks' in project:
            project['tasks'] = [str(task_id) for task_id in project['tasks']]

        # Récupérer les détails de l'équipe
        team = Team.find_by_id(project['team_id'])
        if team:
            team['_id'] = str(team['_id'])
            project['team_details'] = {
                '_id': team['_id'],
                'name': team['name']
            }

            # Récupérer les membres de l'équipe
            members = []
            # Get team memberships
            memberships = list(TeamMember.find_by_team(team['_id']))
            for membership in memberships:
                member = User.find_by_id(membership['user_id'])
                if member:
                    members.append({
                        '_id': str(member['_id']),
                        'nom': member['nom'],
                        'prenom': member['prenom'],
                        'username': member['username'],
                        'role': membership.get('role', 'member')
                    })
            project['members'] = members

        # Compter les tâches
        project['tasks_count'] = len(project.get('tasks', []))

        # Convertir les dates en strings
        if 'start_date' in project and project['start_date']:
            project['start_date'] = project['start_date'].isoformat()
        if 'end_date' in project and project['end_date']:
            project['end_date'] = project['end_date'].isoformat()
        if 'created_at' in project and project['created_at']:
            project['created_at'] = project['created_at'].isoformat()
        if 'updated_at' in project and project['updated_at']:
            project['updated_at'] = project['updated_at'].isoformat()

        return jsonify(project)

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500


@project_bp.route('/add_project_comment', methods=['POST'])
def add_project_comment():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation
        if not all([data.get('project_id'), data.get('content')]):
            return jsonify({"error": "Données manquantes"}), 400

        # Vérifier que l'utilisateur a accès au projet
        project = Project.find_by_id(data['project_id'])
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        team = Team.find_by_id(project['team_id'])

        if not TeamMember.is_member(team['_id'], session['user_id']):
            return jsonify({"error": "Action non autorisée"}), 403

        # Créer le commentaire
        comment_id = Project.add_comment(data['project_id'], session['user_id'], data['content'])

        # Récupérer les infos de l'utilisateur pour la réponse
        user = User.find_by_id(session['user_id'])
        user_info = {
            "_id": str(user['_id']),
            "prenom": user['prenom'],
            "nom": user['nom'],
            "username": user['username']
        }

        return jsonify({
            "success": True,
            "comment": {
                "_id": str(comment_id),
                "content": data['content'],
                "created_at": datetime.now(UTC).isoformat(),
                "user": user_info
            }
        })

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@project_bp.route('/get_project_comments')
def get_project_comments():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"error": "ID de projet manquant"}), 400

    try:
        # Vérifier que l'utilisateur a accès au projet
        project = Project.find_by_id(project_id)
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        team = Team.find_by_id(project['team_id'])

        if not TeamMember.is_member(team['_id'], session['user_id']):
            return jsonify({"error": "Action non autorisée"}), 403

        # Récupérer les commentaires
        comments = Project.get_comments(project_id)

        # Formater les commentaires pour la réponse
        formatted_comments = []
        for comment in comments:
            user = User.find_by_id(comment['user_id'])
            formatted_comment = {
                "_id": str(comment['_id']),
                "content": comment['content'],
                "created_at": comment['created_at'].isoformat(),
                "updated_at": comment['updated_at'].isoformat(),
                "user": {
                    "_id": str(user['_id']),
                    "prenom": user['prenom'],
                    "nom": user['nom'],
                    "username": user['username']
                }
            }
            formatted_comments.append(formatted_comment)

        return jsonify(formatted_comments)

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@project_bp.route('/update_project/<project_id>', methods=['PUT'])
def update_project(project_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # 1. Vérifier que le projet existe et que l'utilisateur est autorisé
        project = Project.find_by_id(project_id)
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        # Seul le créateur ou un membre de l'équipe peut modifier le projet
        user_id = ObjectId(session['user_id'])
        team = Team.find_by_id(project['team_id'])

        if user_id != project['created_by'] and not TeamMember.is_member(team['_id'], session['user_id']):
            return jsonify({"error": "Action non autorisée"}), 403

        # 2. Récupérer les données du formulaire
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données manquantes"}), 400

        # 3. Préparer les mises à jour
        updates = {
            "name": data.get("name", project["name"]).strip(),
            "description": data.get("description", project.get("description", "")).strip(),
            "team_id": data.get("team_id", str(project["team_id"])),
            "status": data.get("status", project["status"])
        }

        # Validation du nom
        if not updates["name"]:
            return jsonify({"error": "Le nom du projet est obligatoire"}), 400

        # Gestion des dates
        if data.get("start_date"):
            updates["start_date"] = datetime.strptime(data["start_date"], '%Y-%m-%d')
        elif "start_date" in project:
            updates["start_date"] = project["start_date"]

        if data.get("end_date"):
            updates["end_date"] = datetime.strptime(data["end_date"], '%Y-%m-%d')
        elif "end_date" in project:
            updates["end_date"] = project["end_date"]

        # 4. Vérifier que la nouvelle équipe existe et que l'utilisateur en fait partie
        new_team = Team.find_by_id(updates["team_id"])
        if not new_team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        if not TeamMember.is_member(new_team['_id'], session['user_id']) and user_id != project['created_by']:
            return jsonify({"error": "Vous devez faire partie de la nouvelle équipe"}), 403

        # 5. Appliquer les modifications
        Project.update(project_id, updates)

        return jsonify({"success": True, "message": "Projet mis à jour avec succès"})

    except ValueError as e:
        return jsonify({"error": "Format de date invalide (YYYY-MM-DD)"}), 400
    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@project_bp.route('/delete_project/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # 1. Vérifier que le projet existe
        project = Project.find_by_id(project_id)
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        # 2. Vérifier les droits (créateur ou chef d'équipe)
        user_id = ObjectId(session['user_id'])
        team = Team.find_by_id(project['team_id'])

        # Check if user is creator or team leader
        # Note: We still use team['chef'] as we keep this field in the team document
        is_leader = user_id == team['chef']

        if user_id != project['created_by'] and not is_leader:
            return jsonify({"error": "Action non autorisée"}), 403

        # 3. Supprimer le projet
        if Project.delete(project_id):
            return jsonify({"success": True, "message": "Projet supprimé avec succès"})
        else:
            return jsonify({"error": "Échec de la suppression"}), 500

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@project_bp.route('/get_user_projects')
def get_user_projects():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Récupérer les équipes de l'utilisateur
        user_teams = list(Team.find_by_member(session['user_id']))
        team_ids = [team['_id'] for team in user_teams]

        # Récupérer les projets de ces équipes
        user_projects = []
        for team_id in team_ids:
            projects = Project.find_by_team(team_id)
            for project in projects:
                # Convertir ObjectId en string et formater les données
                project_data = {
                    "_id": str(project["_id"]),
                    "name": project["name"],
                    "tasks": [str(task_id) for task_id in project.get("tasks", [])],
                    "description": project.get("description", ""),
                    "start_date": project.get("start_date", ""),
                    "end_date": project.get("end_date", ""),
                    "status": project.get("status", "active"),
                    "team_id": str(project["team_id"]),
                    "created_at": project.get("created_at", ""),
                    "updated_at": project.get("updated_at", ""),
                    "team_name": Team.find_by_id(project["team_id"])["name"],
                }
                user_projects.append(project_data)

        return jsonify(user_projects)

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500
