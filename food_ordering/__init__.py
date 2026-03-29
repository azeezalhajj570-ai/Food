from flask import Flask, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

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
        _ensure_schema_updates()

    return app


def _ensure_schema_updates():
    inspector = inspect(db.engine)
    user_columns = {column["name"] for column in inspector.get_columns("user")}

    if "username" not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN username VARCHAR(80)"))
        db.session.commit()

    users = db.session.execute(text("SELECT id, name, email, username FROM user")).fetchall()
    seen_usernames = set()
    for user in users:
        username = user.username or _generate_username(user.name, user.email, seen_usernames)
        seen_usernames.add(username)
        db.session.execute(
            text("UPDATE user SET username = :username WHERE id = :user_id"),
            {"username": username, "user_id": user.id},
        )
    db.session.commit()

    existing_indexes = {index["name"] for index in inspector.get_indexes("user")}
    if "ix_user_username" not in existing_indexes:
        db.session.execute(text("CREATE UNIQUE INDEX ix_user_username ON user (username)"))
        db.session.commit()


def _generate_username(name, email, seen_usernames):
    base = "".join(ch.lower() for ch in (name or "").strip() if ch.isalnum())
    if not base:
        base = (email or "user").split("@", 1)[0].lower()
    if not base:
        base = "user"

    candidate = base[:40]
    suffix = 1
    while candidate in seen_usernames:
        suffix += 1
        candidate = f"{base[:35]}{suffix}"
    return candidate
