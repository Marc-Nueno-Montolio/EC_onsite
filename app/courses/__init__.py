from flask import Blueprint, current_app, send_from_directory
import os
import importlib
import inspect
from datetime import datetime
from flask_login import current_user
from app.database import db
from app.models import UserProgress
import json

# Create blueprint without registering
courses_bp = Blueprint('courses', __name__, url_prefix='/courses')
from app.courses import routes

# Serve media files from each course's media folder
@courses_bp.route('/<course_id>/media/<path:filename>')
def serve_media(course_id, filename):
    courses_dir = os.path.dirname(__file__)
    media_path = os.path.join(courses_dir, course_id, 'media')
    return send_from_directory(media_path, filename)

def init_app(app):
    """
    Initialize the courses blueprint with the app
    """
    with app.app_context():
        register_course_routes()
        # Register blueprint only once here
        app.register_blueprint(courses_bp)

def register_course_routes():
    """
    Dynamically registers all course routes and prints debug information
    """
    courses_dir = os.path.dirname(__file__)
    print("\n=== Starting Course Route Registration ===")
    
    # First register the main courses routes
    try:
        from app.courses import routes
        print("✓ Registered main courses routes")
    except Exception as e:
        print(f"✗ Error loading main courses routes: {e}")

    registered_routes = []
    
    # Skip these directories during scanning
    skip_dirs = {'__pycache__', 'static', 'templates'}

    for course in os.listdir(courses_dir):
        if course in skip_dirs or course.startswith('.'):
            continue
            
        course_path = os.path.join(courses_dir, course)
        if not os.path.isdir(course_path):
            continue

        print(f"\nScanning course: {course}")
        sections_path = os.path.join(course_path, 'sections')
        
        if not os.path.exists(sections_path):
            print(f"  ✗ No sections directory found in {course}")
            continue

        for section in os.listdir(sections_path):
            if section in skip_dirs or section.startswith('.'):
                continue
                
            section_path = os.path.join(sections_path, section)
            if not os.path.isdir(section_path):
                continue

            route_file = os.path.join(section_path, 'route.py')
            if os.path.exists(route_file):
                module_path = f'app.courses.{course}.sections.{section}.route'
                try:
                    module = importlib.import_module(module_path)
                    registered_routes.append({
                        'course': course,
                        'section': section,
                        'module': module
                    })
                    print(f"  ✓ Loaded routes from: {module_path}")
                except Exception as e:
                    print(f"  ✗ Error loading {module_path}: {e}")
            else:
                print(f"  - No route.py in section: {section}")

    # Print all registered routes
    print("\n=== Registered Routes ===")
    base_url = "http://localhost:5000"  # Adjust based on your config
    
    # Print main blueprint routes
    print("\nMain Course Routes:")
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint.startswith('courses.'):
            print(f"  {rule.methods} {base_url}{rule}")

    # Print section routes
    print("\nSection Routes:")
    for route_info in registered_routes:
        print(f"\n{route_info['course']}/{route_info['section']}:")
        for name, obj in inspect.getmembers(route_info['module']):
            if inspect.isfunction(obj) and hasattr(obj, '_endpoint'):
                print(f"  - {name}: {obj.methods if hasattr(obj, 'methods') else ['GET']}")

    print("\n=== Route Registration Complete ===\n")
