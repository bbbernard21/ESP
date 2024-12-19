from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # Import models to ensure they are known to Flask-Migrate
        from app.models import user, academic, communication

        # Register blueprints
        from app.routes.auth import auth as auth_blueprint
        from app.routes.main import main as main_blueprint
        from app.routes.academic import academic as academic_blueprint
        from app.routes.communication import communication as communication_blueprint

        app.register_blueprint(auth_blueprint)
        app.register_blueprint(main_blueprint)
        app.register_blueprint(academic_blueprint)
        app.register_blueprint(communication_blueprint)

    return app 