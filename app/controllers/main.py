from flask import Blueprint, render_template, session, redirect, url_for

# Create a blueprint for the main routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html')
    return render_template('dashboard.html')

@main_bp.route("/fonctionnalite")
def fonctionnalite():
    return render_template('fonctionnalite.html')

@main_bp.route("/apropos")
def apropos():
    return render_template('apropos.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')

@main_bp.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    
    return render_template("dashboard.html")

@main_bp.route('/calendrier')
def calendrier():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    
    return render_template("calendrier.html")

@main_bp.route('/moncompte')
def moncompte():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    return render_template("moncompte.html")