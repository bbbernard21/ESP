from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config
import os

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

    # Create upload directories
    os.makedirs(os.path.join(app.instance_path, 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'uploads', 'submissions'), exist_ok=True)

    with app.app_context():
        # Import models to ensure they are known to Flask-Migrate
        from app.models import user, academic, communication

        # Register blueprints
        from app.routes.auth import auth as auth_blueprint
        from app.routes.main import main as main_blueprint
        from app.routes.academic import academic as academic_blueprint
        from app.routes.communication import communication as communication_blueprint
        from app.routes.admin import admin as admin_blueprint
        from app.routes.professor import professor as professor_blueprint
        from app.routes.student import student as student_blueprint

        app.register_blueprint(auth_blueprint)
        app.register_blueprint(main_blueprint)
        app.register_blueprint(academic_blueprint)
        app.register_blueprint(communication_blueprint)
        app.register_blueprint(admin_blueprint, url_prefix='/admin')
        app.register_blueprint(professor_blueprint)
        app.register_blueprint(student_blueprint)

        # Register error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            app.logger.error(f'Server Error: {error}')
            return render_template('errors/500.html'), 500

        # Initialize scheduler for automated tasks
        from app.scheduler import init_scheduler
        init_scheduler()

    return app 