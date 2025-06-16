from app.models.database import projx_db, project_comments
import bcrypt
from datetime import datetime, UTC


def users():
    data = {
        "nom": "dupont",
        "prenom": "jean baptiste",
        "username": "JB",
        "email": "jeanbaptiste@gmail.com",
        "password": "Mon MotDePasse hashé",
        "is_admin": False,
        "created_at": datetime.now(UTC)
    }
    project_comments.insert_one(data)