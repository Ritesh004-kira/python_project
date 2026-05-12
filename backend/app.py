"""
backend/app.py
Flask application factory.
"""
import os
import sys

# Make the backend package importable when running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from backend.models.database import db

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR  = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR    = os.path.join(BASE_DIR, 'frontend', 'static')
DB_PATH       = os.path.join(BASE_DIR, 'backend', 'instance', 'moctale.db')


def create_app():
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=STATIC_DIR,
    )
    app.config['SECRET_KEY']                = 'super-secret-key-for-moctale'
    app.config['SQLALCHEMY_DATABASE_URI']   = f'sqlite:///{DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        from backend.routes.main   import main_bp
        from backend.routes.auth   import auth_bp
        from backend.routes.movies import movies_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(movies_bp)

        # Create tables (including recommendation_cache on first run)
        db.create_all()

        # Purge expired cache rows from previous sessions
        try:
            from backend.models.database import RecommendationCache
            RecommendationCache.purge_expired()
        except Exception:
            pass

    return app
