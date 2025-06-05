from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.user import User

# Create a blueprint for the auth routes
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signUp')
def signup():
    return render_template('signUp.html')

@auth_bp.route('/signIn')
def signin():
    return render_template('signIn.html')

@auth_bp.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        try:
            # [1] Récupération des données du formulaire
            nom = request.form.get('nom', '').strip()
            prenom = request.form.get('prenom', '').strip()
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirmPassword', '')

            # [2] Validation
            if not all([nom, prenom, username, email, password, confirm_password]):
                flash('Tous les champs sont obligatoires', 'error')
                return redirect(url_for('auth.signup'))

            if password != confirm_password:
                flash('Les mots de passe ne correspondent pas', 'error')
                return redirect(url_for('auth.signup'))

            if not any(char.isupper() for char in password):
                flash('Le mot de passe doit contenir au moins une lettre majuscule', 'error')
                return redirect(url_for('auth.signup'))

            if len(password) < 8:
                flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
                return redirect(url_for('auth.signup'))

            if User.find_by_email(email):
                flash('Cet email est déjà utilisé', 'error')
                return redirect(url_for('auth.signup'))

            if User.find_by_username(username):
                flash('Ce username est déjà utilisé', 'error')
                return redirect(url_for('auth.signup'))

            # [3] Création de l'utilisateur
            user_id = User.create(nom, prenom, username, email, password)

            # [4] Stockage en session
            session['user_id'] = str(user_id)
            session['user_email'] = email
            session['nom'] = nom
            session['prenom'] = prenom
            session['username'] = username

            return redirect(url_for('main.dashboard'))

        except Exception as e:
            flash("Erreur technique", 'error')
            return redirect(url_for('auth.signup'))

@auth_bp.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        try:
            # [1] Récupération des données du formulaire
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            # [2] Validation
            if not all([email, password]):
                flash('Tous les champs sont obligatoires', 'error')
                return redirect(url_for('auth.signin'))

            # [3] Recherche de l'utilisateur
            user = User.find_by_email(email)

            if not user:
                flash('Email ou mot de passe incorrect', 'error')
                return redirect(url_for('auth.signin'))

            # [4] Vérification du mot de passe
            if not User.check_password(user, password):
                flash('Email ou mot de passe incorrect', 'error')
                return redirect(url_for('auth.signin'))

            if email == "admin@admin.com" and password == "Admin123456":
                return redirect(url_for('admin.panel'))

            # [5] Stockage en session
            session['user_id'] = str(user['_id'])
            session['user_email'] = user['email']
            session['nom'] = user['nom']
            session['prenom'] = user['prenom']
            session['username'] = user['username']

            return redirect(url_for('main.dashboard'))

        except Exception as e:
            flash("Erreur technique", 'error')
            return redirect(url_for('auth.signin'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@auth_bp.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

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
        user = User.find_by_id(session['user_id'])

        if not user:
            flash('Utilisateur non trouvé', 'error')
            return redirect(url_for('main.moncompte'))

        # Vérifier le mot de passe actuel si changement demandé
        if new_password:
            if not User.check_password(user, current_password):
                flash('Mot de passe actuel incorrect', 'error')
                return redirect(url_for('main.moncompte'))

            if new_password != confirm_password:
                flash('Les nouveaux mots de passe ne correspondent pas', 'error')
                return redirect(url_for('main.moncompte'))

            if len(new_password) < 8:
                flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
                return redirect(url_for('main.moncompte'))

            password_hash = User.hash_password(new_password)
        else:
            password_hash = user['password']

        # Vérifier l'unicité de l'email et du username
        if email != user['email'] and User.find_by_email(email):
            flash('Cet email est déjà utilisé', 'error')
            return redirect(url_for('main.moncompte'))

        if username != user['username'] and User.find_by_username(username):
            flash('Ce nom d\'utilisateur est déjà pris', 'error')
            return redirect(url_for('main.moncompte'))

        # Mettre à jour les informations
        updates = {
            "nom": nom,
            "prenom": prenom,
            "username": username,
            "email": email,
            "password": password_hash
        }

        User.update(session['user_id'], updates)

        # Mettre à jour la session
        session['nom'] = nom
        session['prenom'] = prenom
        session['username'] = username
        session['user_email'] = email

        flash('Informations mises à jour avec succès!', 'success')
        return redirect(url_for('main.moncompte'))

    except Exception as e:
        flash("Erreur technique lors de la mise à jour", 'error')
        return redirect(url_for('main.moncompte'))