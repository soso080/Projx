# This file makes the app directory a Python package
# It will initialize the Flask application

import os
from flask import Flask
from app.models.database import init_db
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = SECRET_KEY

    # Initialize database
    init_db(app)

    # Register blueprints
    from app.controllers.main import main_bp
    from app.controllers.auth import auth_bp
    from app.controllers.team import team_bp
    from app.controllers.project import project_bp
    from app.controllers.task import task_bp
    from app.controllers.notification import notification_bp
    from app.controllers.admin import admin_bp
    from app.utils.contact import contact_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(contact_bp)

    # Context processor


    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    return app
