"""
ProjX - Application de gestion de projets
Ce fichier est maintenant basé sur une architecture MVC.
Toutes les routes ont été déplacées vers les contrôleurs appropriés.
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)