from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from bson import ObjectId
from datetime import datetime, UTC

from app.models.task import Task
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.models.notification import Notification

# Create a blueprint for the task routes
task_bp = Blueprint('task', __name__)

@task_bp.route('/task')
def task():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    project_id = request.args.get('project_id')
    if not project_id:
        return redirect(url_for('project.project'))

    # Récupère le projet
    project = Project.find_by_id(project_id)
    if not project:
        flash("Projet non trouvé", 'error')
        return redirect(url_for('project.project'))

    # Récupère les tâches du projet
    project_tasks = list(Task.find_by_project(project_id))

    # Ajoute les détails de l'assigné à chaque tâche
    for task in project_tasks:
        assigned_user = User.find_by_id(task['assigned_to'])
        if assigned_user:
            task['assigned_to'] = {
                '_id': str(assigned_user['_id']),
                'prenom': assigned_user['prenom'],
                'nom': assigned_user['nom']
            }

    # Récupère les membres de l'équipe pour l'assignation
    team = Team.find_by_id(project['team_id'])
    team_members = []
    if team and 'members' in team:
        for member_id in team['members']:
            member = User.find_by_id(member_id)
            if member:
                team_members.append(member)

    return render_template("task.html",
                           project=project,
                           tasks=project_tasks,
                           team_members=team_members)

@task_bp.route('/create_task', methods=['POST'])
def create_task():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation des données
        if not all([data.get('title'), data.get('assigned_to'), data.get('status')]):
            return jsonify({"error": "Titre, assignation et statut sont obligatoires"}), 400

        # Vérifier que l'utilisateur fait partie de l'équipe du projet
        project = Project.find_by_id(data['project_id'])
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        team = Team.find_by_id(project['team_id'])
        if ObjectId(session['user_id']) not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Créer la tâche
        due_date = datetime.strptime(data['due_date'], '%Y-%m-%d') if data.get('due_date') else None
        task_id = Task.create(
            title=data['title'],
            project_id=data['project_id'],
            assigned_to=data['assigned_to'],
            creator_id=session['user_id'],
            description=data.get('description', ''),
            due_date=due_date,
            status=data['status']
        )

        # Ajouter la tâche au projet
        Project.add_task(data['project_id'], task_id)

        # Créer une notification pour l'utilisateur assigné
        Notification.create(
            user_id=data['assigned_to'],
            message=f"Une nouvelle tâche vous a été assignée: {data['title']}",
            notification_type="task_assigned",
            sender_id=session['user_id'],
            project_id=data['project_id'],
            task_id=str(task_id)
        )

        return jsonify({"success": True, "message": "Tâche créée avec succès", "task_id": str(task_id)})

    except ValueError as e:
        return jsonify({"error": "Format de date invalide (YYYY-MM-DD)"}), 400
    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@task_bp.route('/get_task_details')
def get_task_details():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({"error": "ID de tâche manquant"}), 400

    try:
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        # Convertir ObjectId en string pour JSON
        task['_id'] = str(task['_id'])
        task['project_id'] = str(task['project_id'])
        task['assigned_to'] = str(task['assigned_to'])
        task['created_by'] = str(task['created_by'])

        # Récupérer les infos de l'assigné
        assigned_user = User.find_by_id(task['assigned_to'])
        if assigned_user:
            task['assigned_to_name'] = f"{assigned_user['prenom']} {assigned_user['nom']}"

        return jsonify(task)

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@task_bp.route('/update_task', methods=['PUT'])
def update_task():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation des données
        if not all([data.get('task_id'), data.get('title'), data.get('assigned_to'), data.get('status')]):
            return jsonify({"error": "Données manquantes"}), 400

        # Vérifier que la tâche existe
        task = Task.find_by_id(data['task_id'])
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        # Vérifier les droits (créateur ou assigné)
        user_id = ObjectId(session['user_id'])
        if user_id != task['created_by'] and user_id != task['assigned_to']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Préparer les mises à jour
        updates = {
            "title": data['title'],
            "description": data.get('description', task.get('description', '')),
            "assigned_to": data['assigned_to'],
            "status": data['status']
        }

        if data.get('due_date'):
            updates["due_date"] = datetime.strptime(data['due_date'], '%Y-%m-%d')

        # Mettre à jour la tâche
        Task.update(data['task_id'], updates)

        return jsonify({"success": True, "message": "Tâche mise à jour avec succès"})

    except ValueError as e:
        return jsonify({"error": "Format de date invalide (YYYY-MM-DD)"}), 400
    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@task_bp.route('/delete_task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Vérifier que la tâche existe
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        # Vérifier les droits (créateur seulement)
        if ObjectId(session['user_id']) != task['created_by']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Supprimer la tâche
        if Task.delete(task_id):
            # Supprimer aussi la référence dans le projet
            Project.remove_task(task['project_id'], task_id)

            # Créer une notification pour l'utilisateur assigné
            Notification.create(
                user_id=task['assigned_to'],
                message=f"La tâche '{task['title']}' a été supprimée",
                notification_type="task_deleted",
                sender_id=session['user_id'],
                project_id=str(task['project_id'])
            )
            return jsonify({"success": True, "message": "Tâche supprimée avec succès"})
        else:
            return jsonify({"error": "Échec de la suppression"}), 500

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@task_bp.route('/add_task_comment', methods=['POST'])
def add_task_comment():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation
        if not all([data.get('task_id'), data.get('content')]):
            return jsonify({"error": "Données manquantes"}), 400

        # Vérifier que l'utilisateur a accès à la tâche
        task = Task.find_by_id(data['task_id'])
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        project = Project.find_by_id(task['project_id'])
        team = Team.find_by_id(project['team_id'])

        if ObjectId(session['user_id']) not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Créer le commentaire
        comment_id = Task.add_comment(data['task_id'], session['user_id'], data['content'])

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

@task_bp.route('/get_task_comments')
def get_task_comments():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({"error": "ID de tâche manquant"}), 400

    try:
        # Vérifier que l'utilisateur a accès à la tâche
        task = Task.find_by_id(task_id)
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        project = Project.find_by_id(task['project_id'])
        team = Team.find_by_id(project['team_id'])

        if ObjectId(session['user_id']) not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Récupérer les commentaires
        comments = Task.get_comments(task_id)
        
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

@task_bp.route('/get_user_tasks')
def get_user_tasks():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Récupérer les tâches assignées à l'utilisateur
        user_tasks = list(Task.find_by_assigned_to(session['user_id']))

        # Convertir ObjectId en string et formater les données
        tasks_list = []
        for task in user_tasks:
            tasks_list.append({
                "_id": str(task["_id"]),
                "title": task["title"],
                "description": task.get("description", ""),
                "due_date": task.get("due_date", ""),
                "status": task.get("status", "todo"),
                "assigned_to": str(task["assigned_to"]),
                "project_id": str(task["project_id"])
            })

        return jsonify(tasks_list)

    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500