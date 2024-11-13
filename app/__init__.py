from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from app.database import db
from app.models import User
from app.tools import tools_bp
from flask.cli import FlaskGroup
from app.websocket import sock
from flask_socketio import SocketIO
from datetime import datetime

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # Config
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key'
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    sock.init_app(app)
    socketio.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Add custom Jinja filters
    @app.template_filter('datetime')
    def format_datetime(value):
        if not value:
            return ''
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    
    with app.app_context():
        # Register blueprints
        from app.courses import courses_bp, init_app as init_courses
        from app.auth import auth_bp
        from app.admin import admin_bp
        from app.main import main_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(tools_bp, url_prefix='/tools')
        # Initialize courses
        init_courses(app)
    
    
    
    return app
