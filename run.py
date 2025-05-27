import json

from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, UTC
from flask_mail import Mail, Message
import bcrypt
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'd3480d181ced3ffb01213dc6274969c6'
# app.config['MAIL_SERVER'] = 'smtp.example.com'  # Ex: smtp.gmail.com
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = 'votre_email@example.com'
# app.config['MAIL_PASSWORD'] = 'votre_mot_de_passe'
# app.config['MAIL_DEFAULT_SENDER'] = 'votre_email@example.com'
# mail = Mail(app)
#bdd
client_db = MongoClient("mongodb+srv://soso:soso@cluster0.ggd13ry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
projx_db = client_db["projx"]
users = projx_db["users"]
teams = projx_db["teams"]
tasks = projx_db["tasks"]
projects = projx_db["projects"]

#les_Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signUp')
def signUp():
    return render_template('signUp.html')

@app.route('/signIn')
def signIn():
    return render_template('signIn.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

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


@app.route('/task')
def task():
    if 'user_id' not in session:
        return redirect(url_for('signIn'))

    project_id = request.args.get('project_id')
    if not project_id:
        return redirect(url_for('project'))

    # Récupère le projet avec les détails complets
    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        flash("Projet non trouvé", 'error')
        return redirect(url_for('project'))

    # Récupère les membres de l'équipe pour l'assignation
    team = teams.find_one({"_id": project['team_id']})
    team_members = []
    if team and 'members' in team:
        team_members = list(users.find({
            "_id": {"$in": team['members']}
        }))

    return render_template("task.html",
                           project=project,
                           tasks=project.get('tasks', []),
                           team_members=team_members)

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
            "chef": ObjectId(creator_id),  # Le créateur est chef par défaut
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
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
