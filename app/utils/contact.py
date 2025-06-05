from flask import Blueprint, request, redirect, url_for, flash, render_template
from app.models.contact import Contact

# Create a blueprint for the contact routes
contact_bp = Blueprint('contact_utils', __name__)

@contact_bp.route('/send_contact', methods=['POST'])
def send_contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        subject = request.form.get('subject', '').strip()

        if not name or not email or not message or not subject:
            flash('Tous les champs sont obligatoires.', 'error')
            return redirect(url_for('main.contact'))

        Contact.create(name, email, subject, message)

        flash('Votre message a été envoyé avec succès!', 'success')
        return render_template("contact.html")

    return render_template("contact.html")