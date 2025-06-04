import json

from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, UTC
from flask_mail import Mail, Message
import bcrypt
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'd3480d181ced3ffb01213dc6274969c6'

client_db = MongoClient("mongodb+srv://soso:soso@cluster0.ggd13ry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
projx_db = client_db["projx"]
users = projx_db["users"]
teams = projx_db["teams"]
tasks = projx_db["tasks"]
projects = projx_db["projects"]
notifications = projx_db["notifications"]
task_comments = projx_db["task_comments"]
sprints = projx_db["sprints"]
team_messages = projx_db["team_messages"]
contacts = projx_db["contacts"]
admin_collection = projx_db["admin"]

#les_Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html')
    return render_template('dashboard.html')

@app.route('/signUp')
def signUp():
    return render_template('signUp.html')

@app.route('/signIn')
def signIn():
    return render_template('signIn.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.route('/notification')
def notification():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))
    return render_template("notifications.html")

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    return render_template("dashboard.html")


@app.route('/team')
def team():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    # Récupère toutes les équipes où l'utilisateur est membre
    user_teams = teams.find({
        "members": ObjectId(session['user_id'])
    })

    # Récupère tous les utilisateurs (sauf l'utilisateur courant)
    all_users = users.find({
        "_id": {"$ne": ObjectId(session['user_id'])}
    })

    # Convertit les curseurs en listes
    teams_list = list(user_teams)
    users_list = list(all_users)

    return render_template("team.html",
                           teams=teams_list,
                           all_users=users_list,
                           users=users)


# Routes pour les projets
@app.route('/project')
def project():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    # Récupère les équipes de l'utilisateur
    user_teams = list(teams.find({"members": ObjectId(session['user_id'])}))
    team_ids = [team['_id'] for team in user_teams]

    # Récupère les projets avec les détails complets des équipes
    user_projects = []
    for project in projects.find({"team_id": {"$in": team_ids}}).sort("created_at", -1):
        # Ajoute les détails de l'équipe au projet
        project['team_details'] = next(
            (team for team in user_teams if team['_id'] == project['team_id']),
            None
        )
        user_projects.append(project)

    return render_template("project.html",
                           projects=user_projects,
                           teams=user_teams)

@app.route('/calendrier')
def calendrier():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    return render_template("calendrier.html")


@app.route('/task')
def task():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    project_id = request.args.get('project_id')
    if not project_id:
        return redirect(url_for('project'))

    # Récupère le projet
    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Projet non trouvé", 'error')
        return redirect(url_for('project'))

    # Récupère les tâches du projet depuis la collection tasks
    task_ids = [ObjectId(task_id) for task_id in project.get('tasks', [])]
    project_tasks = list(tasks.find({"_id": {"$in": task_ids}}))

    # Ajoute les détails de l'assigné à chaque tâche
    for task in project_tasks:
        assigned_user = users.find_one({"_id": task['assigned_to']})
        if assigned_user:
            task['assigned_to'] = {
                '_id': str(assigned_user['_id']),
                'prenom': assigned_user['prenom'],
                'nom': assigned_user['nom']
            }

    # Récupère les membres de l'équipe pour l'assignation
    team = teams.find_one({"_id": project['team_id']})
    team_members = []
    if team and 'members' in team:
        team_members = list(users.find({
            "_id": {"$in": team['members']}
        }))

    return render_template("task.html",
                           project=project,
                           tasks=project_tasks,
                           team_members=team_members)

@app.route('/edit_team/<team_id>')
def edit_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    team = teams.find_one({"_id": ObjectId(team_id)})

    if not team:
        flash("Équipe non trouvée", 'error')
        return redirect(url_for('team'))

    # Récupérer les détails des membres
    member_details = list(users.find({"_id": {"$in": team['members']}}))

    return render_template("edit_team.html",
                           team=team,
                           member_details=member_details)


@app.route('/moncompte')
def moncompte():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))
    return render_template("moncompte.html")
#form

# Dans la route register() du fichier run.py, modifiez comme suit :

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        try:
            # [1] Récupération des données du formulaire
            nom = request.form.get('nom', '').strip()
            prenom = request.form.get('prenom', '').strip()
            username = request.form.get('username', '').strip()  # Nouveau champ
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirmPassword', '')

            # [2] Validation
            if not all([nom, prenom, username, email, password, confirm_password]):
                flash('Tous les champs sont obligatoires', 'error')
                return redirect(url_for('signUp'))

            if password != confirm_password:
                flash('Les mots de passe ne correspondent pas', 'error')
                return redirect(url_for('signUp'))

            if not any(char.isupper() for char in password):
                flash('Le mot de passe doit contenir au moins une lettre majuscule', 'error')
                return redirect(url_for('signUp'))

            if len(password) < 8:
                flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
                return redirect(url_for('signUp'))

            if users.find_one({"email": email}):
                flash('Cet email est déjà utilisé', 'error')
                return redirect(url_for('signUp'))

            if users.find_one({"username": username}):  # Vérification de l'unicité du username
                flash('Ce username est déjà utilisé', 'error')
                return redirect(url_for('signUp'))

            # [3] Hachage du mot de passe
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # [4] Insertion dans MongoDB
            result = users.insert_one({
                "nom": nom,
                "prenom": prenom,
                "username": username,
                "email": email,
                "password": password_hash,
                "is_admin": False,  # Nouveau champ
                "created_at": datetime.now(UTC)
            })

            # [5] Stockage en session (CONVERSION EN STRING)
            session['user_id'] = str(result.inserted_id)
            session['user_email'] = email
            session['nom'] = nom
            session['prenom'] = prenom
            session['username'] = username

            return redirect(url_for('dashboard'))

        except Exception as e:
            app.logger.error(f"Erreur inscription: {str(e)}")
            flash("Erreur technique", 'error')
            return redirect(url_for('signUp'))




@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        try:
            # [1] Récupération des données du formulaire
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            # [2] Validation
            if not all([email, password]):
                flash('Tous les champs sont obligatoires', 'error')
                return redirect(url_for('signIn'))

            # [3] Recherche de l'utilisateur dans la base de données
            user = users.find_one({"email": email})

            if not user:
                flash('Email ou mot de passe incorrect', 'error')
                return redirect(url_for('signIn'))

            # [4] Vérification du mot de passe
            if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
                flash('Email ou mot de passe incorrect', 'error')
                return redirect(url_for('signIn'))

            if email == "admin@admin.com" and password == "Admin123456":
                return redirect(url_for('admin'))

            # [5] Stockage en session (CONVERSION EN STRING)
            session['user_id'] = str(user['_id'])
            session['user_email'] = user['email']
            session['nom'] = user['nom']
            session['prenom'] = user['prenom']
            username = user["username"]
            session["username"] = username


            return redirect(url_for('dashboard'))

        except Exception as e:
            app.logger.error(f"Erreur connexion: {str(e)}")
            flash("Erreur technique", 'error')
            return redirect(url_for('signIn'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

######################################db action####################################################
#team crud

@app.route('/get_user_tasks')
def get_user_tasks():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Récupérer les équipes de l'utilisateur
        user_teams = list(teams.find({"members": ObjectId(session['user_id'])}))
        team_ids = [team['_id'] for team in user_teams]

        # Récupérer les projets de ces équipes
        user_projects = list(projects.find({"team_id": {"$in": team_ids}}))
        project_ids = [project['_id'] for project in user_projects]

        # Récupérer toutes les tâches de ces projets
        user_tasks = list(tasks.find({
            "project_id": {"$in": project_ids}
        }))

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
        app.logger.error(f"Erreur récupération tâches: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/get_user_projects')
def get_user_projects():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Récupérer les équipes de l'utilisateur
        user_teams = list(teams.find({"members": ObjectId(session['user_id'])}))
        team_ids = [team['_id'] for team in user_teams]

        # Récupérer les projets de ces équipes
        user_projects = list(projects.find({"team_id": {"$in": team_ids}}))

        # Convertir ObjectId en string et formater les données
        projects_list = []
        for project in user_projects:
            # Gérer le cas où tasks est une chaîne JSON
            if isinstance(project.get('tasks'), str):
                try:
                    tasks_list = json.loads(project['tasks'])
                    # Convertir les strings en ObjectId si nécessaire
                    project['tasks'] = [ObjectId(task_id) if not isinstance(task_id, ObjectId) else task_id
                                      for task_id in tasks_list]
                except json.JSONDecodeError:
                    project['tasks'] = []

            projects_list.append({
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
                "team_name": teams.find_one({"_id": project["team_id"]})["name"],
            })

        return jsonify(projects_list)

    except Exception as e:
        app.logger.error(f"Erreur récupération projets: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/create_team', methods=['POST'])
def create_team():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

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
            return redirect(url_for('team'))

        # 4. Création de l'équipe
        team_data = {
            "name": request.form.get('name').strip(),
            "description": request.form.get('description', '').strip(),
            "created_by": ObjectId(creator_id),
            "chef": ObjectId(creator_id),
            "members": [ObjectId(member) for member in members],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        # Validation supplémentaire
        if not team_data["name"]:
            flash("Le nom de l'équipe est obligatoire", 'error')
            return redirect(url_for('team'))

        teams.insert_one(team_data)
        flash('Équipe créée avec succès!', 'success')
        return redirect(url_for('team'))

    except Exception as e:
        app.logger.error(f"Erreur création équipe: {str(e)}")
        flash("Erreur technique lors de la création", 'error')
        return redirect(url_for('team'))


@app.route('/search_users')
def search_users():
    if 'user_id' not in session:
        return jsonify([])

    query = request.args.get('q', '').lower()
    if len(query) < 2:
        return jsonify([])

    # Recherche dans nom, prénom ou username
    users_list = list(users.find({
        "_id": {"$ne": ObjectId(session['user_id'])},
        "$or": [
            {"nom": {"$regex": query, "$options": "i"}},
            {"prenom": {"$regex": query, "$options": "i"}},
            {"username": {"$regex": query, "$options": "i"}}
        ]
    }, {"nom": 1, "prenom": 1, "username": 1}))

    # Convertir ObjectId en string pour JSON
    for user in users_list:
        user['_id'] = str(user['_id'])

    return jsonify(users_list)


@app.route('/update_team/<team_id>', methods=['PUT'])
def update_team(team_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # 1. Vérifier que l'équipe existe et que l'utilisateur est autorisé
        team = teams.find_one({"_id": ObjectId(team_id)})
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
        current_members = set(team["members"])
        members_to_remove = set(ObjectId(m) for m in data.get("membersToRemove", []))
        new_members = set(ObjectId(m) for m in data.get("newMembers", []))

        # Vérifier que le nouveau chef est toujours membre
        if updates["chef"] not in (current_members - members_to_remove | new_members):
            return jsonify({"error": "Le chef doit être membre de l'équipe"}), 400

        # Mettre à jour la liste des membres
        updated_members = list((current_members - members_to_remove) | new_members)
        updates["members"] = updated_members

        # 5. Appliquer les modifications dans MongoDB
        teams.update_one(
            {"_id": ObjectId(team_id)},
            {"$set": updates}
        )

        return jsonify({"success": True, "message": "Équipe mise à jour avec succès"})

    except Exception as e:
        app.logger.error(f"Erreur mise à jour équipe: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


@app.route('/delete_team/<team_id>', methods=['DELETE'])
def delete_team(team_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Vérifier que l'équipe existe
        team = teams.find_one({"_id": ObjectId(team_id)})
        if not team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        # Seul le créateur peut supprimer l'équipe
        creator_id = team.get("created_by")
        user_id = ObjectId(session['user_id'])

        if user_id != creator_id:
            return jsonify({"error": "Action non autorisée"}), 403

        # Supprimer l'équipe
        result = teams.delete_one({"_id": ObjectId(team_id)})

        if result.deleted_count == 1:
            # Supprimer aussi tous les projets associés à cette équipe
            projects.delete_many({"team_id": ObjectId(team_id)})
            return jsonify({"success": True, "message": "Équipe supprimée avec succès"})
        else:
            return jsonify({"error": "Échec de la suppression"}), 500

    except Exception as e:
        app.logger.error(f"Erreur suppression équipe: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


@app.route('/get_team_details')
def get_team_details():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({"error": "ID d'équipe manquant"}), 400

    try:
        team = teams.find_one({"_id": ObjectId(team_id)})
        if not team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        # Convertir ObjectId en string pour JSON
        team['_id'] = str(team['_id'])
        team['created_by'] = str(team['created_by'])
        team['chef'] = str(team['chef'])

        # Convertir les ObjectId des membres
        team['members'] = [str(member) for member in team['members']]

        # Récupérer les infos du chef
        leader = users.find_one({"_id": ObjectId(team['chef'])})
        if leader:
            leader['_id'] = str(leader['_id'])
            team['leader'] = {
                '_id': leader['_id'],
                'nom': leader['nom'],
                'prenom': leader['prenom'],
                'username': leader['username']
            }

        # Récupérer les infos des membres
        members = list(users.find({"_id": {"$in": [ObjectId(id) for id in team['members']]}}))
        team['members'] = []
        for member in members:
            team['members'].append({
                '_id': str(member['_id']),
                'nom': member['nom'],
                'prenom': member['prenom'],
                'username': member['username']
            })

        return jsonify(team)

    except Exception as e:
        app.logger.error(f"Erreur détails équipe: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

# Route pour créer un projet
@app.route('/create_project', methods=['POST'])
def create_project():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    try:
        # Récupérer les données du formulaire
        name = request.form.get('name').strip()
        description = request.form.get('description', '').strip()
        team_id = request.form.get('team_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status', 'active')

        # Validation
        if not name or not team_id:
            flash('Le nom et l\'équipe sont obligatoires', 'error')
            return redirect(url_for('project'))

        # Convertir les dates
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        # Créer le projet
        project_data = {
            "name": name,
            "description": description,
            "team_id": ObjectId(team_id),
            "created_by": ObjectId(session['user_id']),
            "start_date": start_date_obj,
            "end_date": end_date_obj,
            "status": status,
            "tasks": [],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        projects.insert_one(project_data)
        flash('Projet créé avec succès!', 'success')
        return redirect(url_for('project'))

    except Exception as e:
        app.logger.error(f"Erreur création projet: {str(e)}")
        flash("Erreur technique lors de la création", 'error')
        return redirect(url_for('project'))

# Route pour obtenir les détails d'un projet
@app.route('/get_project_details')
def get_project_details():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"error": "ID de projet manquant"}), 400

    try:
        project = projects.find_one({"_id": ObjectId(project_id)})
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
        team = teams.find_one({"_id": ObjectId(project['team_id'])})
        if team:
            team['_id'] = str(team['_id'])
            project['team_details'] = {
                '_id': team['_id'],
                'name': team['name']
            }

            # Récupérer les membres de l'équipe
            members = list(users.find({"_id": {"$in": team['members']}}))
            project['members'] = []
            for member in members:
                project['members'].append({
                    '_id': str(member['_id']),
                    'nom': member['nom'],
                    'prenom': member['prenom'],
                    'username': member['username']
                })

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
        app.logger.error(f"Erreur détails projet: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

# Route pour éditer un projet (à créer aussi)
@app.route('/edit_project/<project_id>')
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Projet non trouvé", 'error')
        return redirect(url_for('project'))

    # Récupérer les équipes disponibles
    user_teams = list(teams.find({"members": ObjectId(session['user_id'])}))

    return render_template("edit_project.html",
                         project=project,
                         teams=user_teams)


# Route pour mettre à jour un projet
@app.route('/update_project/<project_id>', methods=['PUT'])
def update_project(project_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # 1. Vérifier que le projet existe et que l'utilisateur est autorisé
        project = projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        # Seul le créateur ou un membre de l'équipe peut modifier le projet
        user_id = ObjectId(session['user_id'])
        team = teams.find_one({"_id": project['team_id']})

        if user_id != project['created_by'] and user_id not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # 2. Récupérer les données du formulaire
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données manquantes"}), 400

        # 3. Préparer les mises à jour
        updates = {
            "name": data.get("name", project["name"]).strip(),
            "description": data.get("description", project.get("description", "")).strip(),
            "team_id": ObjectId(data.get("team_id", project["team_id"])),
            "status": data.get("status", project["status"]),
            "updated_at": datetime.now(UTC)
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
        new_team = teams.find_one({"_id": updates["team_id"]})
        if not new_team:
            return jsonify({"error": "Équipe non trouvée"}), 404

        if user_id not in new_team['members'] and user_id != project['created_by']:
            return jsonify({"error": "Vous devez faire partie de la nouvelle équipe"}), 403

        # 5. Appliquer les modifications dans MongoDB
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": updates}
        )

        return jsonify({"success": True, "message": "Projet mis à jour avec succès"})

    except ValueError as e:
        app.logger.error(f"Erreur format date: {str(e)}")
        return jsonify({"error": "Format de date invalide (YYYY-MM-DD)"}), 400
    except Exception as e:
        app.logger.error(f"Erreur mise à jour projet: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Route pour supprimer un projet
@app.route('/delete_project/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # 1. Vérifier que le projet existe
        project = projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        # 2. Vérifier les droits (créateur ou chef d'équipe)
        user_id = ObjectId(session['user_id'])
        team = teams.find_one({"_id": project['team_id']})

        if user_id != project['created_by'] and user_id != team['chef']:
            return jsonify({"error": "Action non autorisée"}), 403

        # 3. Supprimer le projet
        result = projects.delete_one({"_id": ObjectId(project_id)})

        if result.deleted_count == 1:
            # Optionnel: Supprimer aussi toutes les tâches associées si elles sont stockées séparément
            # tasks.delete_many({"project_id": ObjectId(project_id)})
            return jsonify({"success": True, "message": "Projet supprimé avec succès"})
        else:
            return jsonify({"error": "Échec de la suppression"}), 500

    except Exception as e:
        app.logger.error(f"Erreur suppression projet: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Route pour créer une tâche
@app.route('/create_task', methods=['POST'])
def create_task():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation des données
        if not all([data.get('title'), data.get('assigned_to'), data.get('status')]):
            return jsonify({"error": "Titre, assignation et statut sont obligatoires"}), 400

        # Vérifier que l'utilisateur fait partie de l'équipe du projet
        project = projects.find_one({"_id": ObjectId(data['project_id'])})
        if not project:
            return jsonify({"error": "Projet non trouvé"}), 404

        team = teams.find_one({"_id": project['team_id']})
        if ObjectId(session['user_id']) not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Créer la tâche
        task_data = {
            "project_id": ObjectId(data['project_id']),
            "title": data['title'],
            "description": data.get('description', ''),
            "assigned_to": ObjectId(data['assigned_to']),
            "due_date": datetime.strptime(data['due_date'], '%Y-%m-%d') if data.get('due_date') else None,
            "status": data['status'],
            "created_by": ObjectId(session['user_id']),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        # Insérer dans la collection tasks
        result = tasks.insert_one(task_data)
        task_id = result.inserted_id

        # Ajouter aussi la référence dans le projet
        projects.update_one(
            {"_id": ObjectId(data['project_id'])},
            {"$push": {"tasks": ObjectId(task_id)}}
        )

        create_notification(
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
        app.logger.error(f"Erreur création tâche: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Route pour obtenir les détails d'une tâche
@app.route('/get_task_details')
def get_task_details():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({"error": "ID de tâche manquant"}), 400

    try:
        task = tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        # Convertir ObjectId en string pour JSON
        task['_id'] = str(task['_id'])
        task['project_id'] = str(task['project_id'])
        task['assigned_to'] = str(task['assigned_to'])
        task['created_by'] = str(task['created_by'])

        # Récupérer les infos de l'assigné
        assigned_user = users.find_one({"_id": ObjectId(task['assigned_to'])})
        if assigned_user:
            task['assigned_to_name'] = f"{assigned_user['prenom']} {assigned_user['nom']}"

        return jsonify(task)

    except Exception as e:
        app.logger.error(f"Erreur détails tâche: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Ajoutez cette route dans run.py
@app.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    try:
        # Récupérer les données du formulaire
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Récupérer l'utilisateur
        user_id = ObjectId(session['user_id'])
        user = users.find_one({"_id": user_id})

        if not user:
            flash('Utilisateur non trouvé', 'error')
            return redirect(url_for('moncompte'))

        # Vérifier le mot de passe actuel si changement demandé
        if new_password:
            if not bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
                flash('Mot de passe actuel incorrect', 'error')
                return redirect(url_for('moncompte'))

            if new_password != confirm_password:
                flash('Les nouveaux mots de passe ne correspondent pas', 'error')
                return redirect(url_for('moncompte'))

            if len(new_password) < 8:
                flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
                return redirect(url_for('moncompte'))

            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        else:
            password_hash = user['password']

        # Vérifier l'unicité de l'email et du username
        if email != user['email'] and users.find_one({"email": email, "_id": {"$ne": user_id}}):
            flash('Cet email est déjà utilisé', 'error')
            return redirect(url_for('moncompte'))

        if username != user['username'] and users.find_one({"username": username, "_id": {"$ne": user_id}}):
            flash('Ce nom d\'utilisateur est déjà pris', 'error')
            return redirect(url_for('moncompte'))

        # Mettre à jour les informations
        updates = {
            "nom": nom,
            "prenom": prenom,
            "username": username,
            "email": email,
            "password": password_hash,
            "updated_at": datetime.now(UTC)
        }

        users.update_one({"_id": user_id}, {"$set": updates})

        # Mettre à jour la session
        session['nom'] = nom
        session['prenom'] = prenom
        session['username'] = username
        session['user_email'] = email

        flash('Informations mises à jour avec succès!', 'success')
        return redirect(url_for('moncompte'))

    except Exception as e:
        app.logger.error(f"Erreur mise à jour compte: {str(e)}")
        flash("Erreur technique lors de la mise à jour", 'error')
        return redirect(url_for('moncompte'))

# Route pour mettre à jour une tâche
@app.route('/update_task', methods=['PUT'])
def update_task():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation des données
        if not all([data.get('task_id'), data.get('title'), data.get('assigned_to'), data.get('status')]):
            return jsonify({"error": "Données manquantes"}), 400

        # Vérifier que la tâche existe
        task = tasks.find_one({"_id": ObjectId(data['task_id'])})
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
            "assigned_to": ObjectId(data['assigned_to']),
            "status": data['status'],
            "updated_at": datetime.now(UTC)
        }

        if data.get('due_date'):
            updates["due_date"] = datetime.strptime(data['due_date'], '%Y-%m-%d')

        # Mettre à jour la tâche
        tasks.update_one(
            {"_id": ObjectId(data['task_id'])},
            {"$set": updates}
        )

        return jsonify({"success": True, "message": "Tâche mise à jour avec succès"})

    except ValueError as e:
        return jsonify({"error": "Format de date invalide (YYYY-MM-DD)"}), 400
    except Exception as e:
        app.logger.error(f"Erreur mise à jour tâche: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Route pour supprimer une tâche
@app.route('/delete_task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Vérifier que la tâche existe
        task = tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        # Vérifier les droits (créateur seulement)
        if ObjectId(session['user_id']) != task['created_by']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Supprimer la tâche
        result = tasks.delete_one({"_id": ObjectId(task_id)})

        if result.deleted_count == 1:
            # Supprimer aussi la référence dans le projet
            projects.update_one(
                {"_id": task['project_id']},
                {"$pull": {"tasks": ObjectId(task_id)}}
            )

            create_notification(
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
        app.logger.error(f"Erreur suppression tâche: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Ajoutez ces routes dans run.py

@app.route('/get_notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Vérifier si on veut toutes les notifications ou seulement les non lues
        all_notifications = request.args.get('all', 'false').lower() == 'true'

        query = {"user_id": ObjectId(session['user_id'])}
        if not all_notifications:
            query["read"] = False

        # Récupérer les notifications
        user_notifications = list(notifications.find(query)
                                  .sort("created_at", -1)
                                  .limit(50 if all_notifications else 10))

        # Convertir ObjectId en string
        for notif in user_notifications:
            notif['_id'] = str(notif['_id'])
            notif['user_id'] = str(notif['user_id'])
            if 'sender_id' in notif:
                notif['sender_id'] = str(notif['sender_id'])
            if 'project_id' in notif:
                notif['project_id'] = str(notif['project_id'])
            if 'task_id' in notif:
                notif['task_id'] = str(notif['task_id'])

        return jsonify(user_notifications)
    except Exception as e:
        app.logger.error(f"Erreur récupération notifications: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/mark_notification_as_read/<notification_id>', methods=['POST'])
def mark_notification_as_read(notification_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        result = notifications.update_one(
            {"_id": ObjectId(notification_id), "user_id": ObjectId(session['user_id'])},
            {"$set": {"read": True, "read_at": datetime.now(UTC)}}
        )

        if result.modified_count == 1:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Notification non trouvée"}), 404
    except Exception as e:
        app.logger.error(f"Erreur marquage notification: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/mark_all_notifications_as_read', methods=['POST'])
def mark_all_notifications_as_read():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        notifications.update_many(
            {"user_id": ObjectId(session['user_id']), "read": False},
            {"$set": {"read": True, "read_at": datetime.now(UTC)}}
        )
        return jsonify({"success": True})
    except Exception as e:
        app.logger.error(f"Erreur marquage notifications: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

# Fonction utilitaire pour créer des notifications
def create_notification(user_id, message, notification_type, sender_id=None, project_id=None, task_id=None):
    try:
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

        notifications.insert_one(notification_data)
    except Exception as e:
        app.logger.error(f"Erreur création notification: {str(e)}")


# Route pour ajouter un commentaire à une tâche
@app.route('/add_task_comment', methods=['POST'])
def add_task_comment():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        data = request.get_json()

        # Validation
        if not all([data.get('task_id'), data.get('content')]):
            return jsonify({"error": "Données manquantes"}), 400

        # Vérifier que l'utilisateur a accès à la tâche
        task = tasks.find_one({"_id": ObjectId(data['task_id'])})
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        project = projects.find_one({"_id": task['project_id']})
        team = teams.find_one({"_id": project['team_id']})

        if ObjectId(session['user_id']) not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Créer le commentaire
        comment_data = {
            "task_id": ObjectId(data['task_id']),
            "user_id": ObjectId(session['user_id']),
            "content": data['content'],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        result = task_comments.insert_one(comment_data)
        comment_id = str(result.inserted_id)

        # Récupérer les infos de l'utilisateur pour la réponse
        user = users.find_one({"_id": ObjectId(session['user_id'])})
        user_info = {
            "_id": str(user['_id']),
            "prenom": user['prenom'],
            "nom": user['nom'],
            "username": user['username']
        }

        return jsonify({
            "success": True,
            "comment": {
                "_id": comment_id,
                "content": data['content'],
                "created_at": comment_data['created_at'].isoformat(),
                "user": user_info
            }
        })

    except Exception as e:
        app.logger.error(f"Erreur ajout commentaire: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500


# Route pour récupérer les commentaires d'une tâche
@app.route('/get_task_comments')
def get_task_comments():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({"error": "ID de tâche manquant"}), 400

    try:
        # Vérifier que l'utilisateur a accès à la tâche
        task = tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            return jsonify({"error": "Tâche non trouvée"}), 404

        project = projects.find_one({"_id": task['project_id']})
        team = teams.find_one({"_id": project['team_id']})

        if ObjectId(session['user_id']) not in team['members']:
            return jsonify({"error": "Action non autorisée"}), 403

        # Récupérer les commentaires avec les infos des utilisateurs
        comments = list(task_comments.aggregate([
            {"$match": {"task_id": ObjectId(task_id)}},
            {"$sort": {"created_at": 1}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$project": {
                "content": 1,
                "created_at": 1,
                "updated_at": 1,
                "user._id": 1,
                "user.prenom": 1,
                "user.nom": 1,
                "user.username": 1
            }}
        ]))

        # Convertir les dates et ObjectId
        for comment in comments:
            comment['_id'] = str(comment['_id'])
            comment['user']['_id'] = str(comment['user']['_id'])
            comment['created_at'] = comment['created_at'].isoformat()
            comment['updated_at'] = comment['updated_at'].isoformat()

        return jsonify(comments)

    except Exception as e:
        app.logger.error(f"Erreur récupération commentaires: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/send_contact', methods=['POST'])
def send_contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        subject = request.form.get('subject', '').strip()

        if not name or not email or not message or not subject:
            flash('Tous les champs sont obligatoires.', 'error')
            return redirect(url_for('contact'))

        data = {
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
        }
        contacts.insert_one(data)

        flash('Votre message a été envoyé avec succès!', 'success')
        return render_template("contact.html")

    return render_template("contact.html")


# Ajoutez ces routes à votre fichier run.py

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    # Vérifiez si l'utilisateur est admin (vous devrez ajouter un champ is_admin à votre modèle User)
    user = users.find_one({"_id": ObjectId(session['user_id'])})
    if not user.get('is_admin', False):
        flash("Accès refusé : vous n'avez pas les droits d'administration", 'error')
        return redirect(url_for('dashboard'))

    return render_template("admin.html")


@app.route('/admin/stats')
def admin_stats():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = users.find_one({"_id": ObjectId(session['user_id'])})
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    stats = {
        "users": users.count_documents({}),
        "teams": teams.count_documents({}),
        "projects": projects.count_documents({}),
        "contacts": contacts.count_documents({})
    }

    return jsonify(stats)


@app.route('/admin/messages')
def admin_messages():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = users.find_one({"_id": ObjectId(session['user_id'])})
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    # Récupérer les paramètres de pagination et de filtre
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    filter_type = request.args.get('filter', 'all')

    # Construire la requête en fonction du filtre
    query = {}
    if filter_type != 'all':
        query = {"subject": filter_type}

    # Compter le nombre total de messages
    total = contacts.count_documents(query)

    # Récupérer les messages paginés
    messages = list(contacts.find(query)
                    .sort("created_at", -1)
                    .skip((page - 1) * per_page)
                    .limit(per_page))

    # Convertir ObjectId en string
    for message in messages:
        message['_id'] = str(message['_id'])

    return jsonify({
        "messages": messages,
        "total": total,
        "page": page,
        "per_page": per_page
    })


@app.route('/admin/messages/<message_id>')
def admin_message_detail(message_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = users.find_one({"_id": ObjectId(session['user_id'])})
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    message = contacts.find_one({"_id": ObjectId(message_id)})
    if not message:
        return jsonify({"error": "Message non trouvé"}), 404

    message['_id'] = str(message['_id'])
    return jsonify(message)


@app.route('/admin/messages/<message_id>', methods=['DELETE'])
def admin_delete_message(message_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = users.find_one({"_id": ObjectId(session['user_id'])})
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    result = contacts.delete_one({"_id": ObjectId(message_id)})
    if result.deleted_count == 1:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Message non trouvé"}), 404


@app.route

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
