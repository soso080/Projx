from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from bson import ObjectId

from app.models.user import User
from app.models.team import Team
from app.models.project import Project
from app.models.contact import Contact
from app.models.database import projx_db

# Create a blueprint for the admin routes
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def panel():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    # Vérifiez si l'utilisateur est admin
    user = User.find_by_id(session['user_id'])
    if not user.get('is_admin', False):
        flash("Accès refusé : vous n'avez pas les droits d'administration", 'error')
        return redirect(url_for('main.dashboard'))

    return render_template("admin.html")

@admin_bp.route('/admin/stats')
def stats():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = User.find_by_id(session['user_id'])
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    stats = {
        "users": projx_db["users"].count_documents({}),
        "teams": projx_db["teams"].count_documents({}),
        "projects": projx_db["projects"].count_documents({}),
        "contacts": projx_db["contacts"].count_documents({})
    }

    return jsonify(stats)

@admin_bp.route('/admin/messages')
def messages():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = User.find_by_id(session['user_id'])
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    # Récupérer les paramètres de pagination et de filtre
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    filter_type = request.args.get('filter', 'all')

    # Récupérer les messages paginés
    result = Contact.find_all(page, per_page, filter_type)
    
    # Convertir ObjectId en string
    for message in result["messages"]:
        message['_id'] = str(message['_id'])

    return jsonify(result)

@admin_bp.route('/admin/messages/<message_id>')
def message_detail(message_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = User.find_by_id(session['user_id'])
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    message = Contact.find_by_id(message_id)
    if not message:
        return jsonify({"error": "Message non trouvé"}), 404

    message['_id'] = str(message['_id'])
    return jsonify(message)

@admin_bp.route('/admin/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    user = User.find_by_id(session['user_id'])
    if not user.get('is_admin', False):
        return jsonify({"error": "Accès refusé"}), 403

    if Contact.delete(message_id):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Message non trouvé"}), 404