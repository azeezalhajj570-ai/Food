from flask import Flask, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from food_ordering.routes.api import api_bp
    from food_ordering.routes.auth import auth_bp
    from food_ordering.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.context_processor
    def inject_shared_template_state():
        from food_ordering.services.cart import get_cart_summary

        return {"cart_summary": get_cart_summary(session)}

    with app.app_context():
        db.create_all()

    return app
