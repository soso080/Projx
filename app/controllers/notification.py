from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from bson import ObjectId

from app.models.notification import Notification

# Create a blueprint for the notification routes
notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/notification')
def notification():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    return render_template("notifications.html")

@notification_bp.route('/get_notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        # Vérifier si on veut toutes les notifications ou seulement les non lues
        all_notifications = request.args.get('all', 'false').lower() == 'true'
        
        # Récupérer les notifications
        user_notifications = Notification.find_by_user(
            user_id=session['user_id'],
            unread_only=not all_notifications,
            limit=50 if all_notifications else 10
        )

        # Convertir en liste et formater pour JSON
        notifications_list = []
        for notif in user_notifications:
            notification_data = {
                '_id': str(notif['_id']),
                'user_id': str(notif['user_id']),
                'message': notif['message'],
                'type': notif['type'],
                'read': notif['read'],
                'created_at': notif['created_at'].isoformat()
            }
            
            if 'sender_id' in notif:
                notification_data['sender_id'] = str(notif['sender_id'])
            if 'project_id' in notif:
                notification_data['project_id'] = str(notif['project_id'])
            if 'task_id' in notif:
                notification_data['task_id'] = str(notif['task_id'])
            if 'read_at' in notif and notif['read_at']:
                notification_data['read_at'] = notif['read_at'].isoformat()
                
            notifications_list.append(notification_data)

        return jsonify(notifications_list)
    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@notification_bp.route('/mark_notification_as_read/<notification_id>', methods=['POST'])
def mark_notification_as_read(notification_id):
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        if Notification.mark_as_read(notification_id, session['user_id']):
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Notification non trouvée"}), 404
    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500

@notification_bp.route('/mark_all_notifications_as_read', methods=['POST'])
def mark_all_notifications_as_read():
    if 'user_id' not in session:
        return jsonify({"error": "Non autorisé"}), 401

    try:
        count = Notification.mark_all_as_read(session['user_id'])
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"error": "Erreur serveur"}), 500