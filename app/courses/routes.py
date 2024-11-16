from flask import render_template, redirect, url_for, request, flash, jsonify
from app.courses import courses_bp as bp
import os, json, markdown
import importlib
import inspect
from flask_login import current_user, login_required
from app.models import SectionCompletion, User
from app.database import db
from markdown.extensions import fenced_code
from markdown.extensions import tables
from markdown.extensions import toc
from markdown.extensions.codehilite import CodeHiliteExtension

@bp.route('/')
@login_required
def list():
    courses = get_courses()
    
    # Get completion data for current user
    if current_user.is_authenticated:
        completions = SectionCompletion.query.filter_by(user_id=current_user.id).all()
        completion_map = {(c.course_id, c.section_id) for c in completions}
        
        # Calculate completion percentage for each course
        for course in courses:
            total_sections = len(course['sections'])
            completed_sections = sum(
                1 for section in course['sections'] 
                if (course['id'], section) in completion_map
            )
            course['completion'] = round((completed_sections / total_sections) * 100)
    
    return render_template('courses/list.html', courses=courses)

@bp.route('/<course_id>')
def launch_course(course_id):
    # Redirect to first section of the course
    # get the first section from the course.json
    courses_dir = os.path.dirname(__file__)
    course_path = os.path.join(courses_dir, course_id)
    course_json = os.path.join(course_path, 'course.json')
    with open(course_json) as f:
        course = json.load(f)
        first_section = course['sections'][0]
    return redirect(url_for('courses.section_details', 
                          course_id=course_id, 
                          section_id=first_section))  # Adjust section ID as needed

@bp.route('/<course_id>/<section_id>/mark-complete', methods=['POST'])
@login_required
def mark_complete(course_id, section_id):
    try:
        # Check if already completed
        completion = SectionCompletion.query.filter_by(
            user_id=current_user.id,
            course_id=course_id,
            section_id=section_id
        ).first()
        
        if completion:
            # Toggle completion status
            db.session.delete(completion)
            message = 'Section marked as incomplete'
        else:
            # Mark as complete
            completion = SectionCompletion(
                user_id=current_user.id,
                course_id=course_id,
                section_id=section_id
            )
            db.session.add(completion)
            message = 'Section marked as complete'
            
        db.session.commit()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<course_id>/<section_id>')
@login_required
def section_details(course_id, section_id):
    # Add completion check
    is_completed = False
    if current_user.is_authenticated:
        completion = SectionCompletion.query.filter_by(
            user_id=current_user.id,
            course_id=course_id,
            section_id=section_id
        ).first()
        is_completed = completion is not None

    # Get section's route module
    section_path = f'app.courses.{course_id}.sections.{section_id}.route'
    init_failed = False
    init_error = None
    
    try:
        route_module = importlib.import_module(section_path)
        
        # Find and execute init function if it exists
        for name, func in inspect.getmembers(route_module):
            if inspect.isfunction(func) and hasattr(func, '_init'):
                result = func(course_id=course_id, section_id=section_id)
                if not result.get('valid', False):
                    init_failed = True
                    init_error = result.get('message', 'Unknown error')
                break
                
    except ImportError:
        # No route module or init function - continue normally
        pass
    except Exception as e:
        init_failed = True
        init_error = str(e)

    # Get course info
    courses_dir = os.path.dirname(__file__)
    course_path = os.path.join(courses_dir, course_id)
    course_json = os.path.join(course_path, 'course.json')
    
    with open(course_json) as f:
        course = json.load(f)
        course['id'] = course_id
        
        # Add image URL if present
        if 'image' in course:
            course['image'] = url_for('courses.serve_media', 
                                    course_id=course_id, 
                                    filename=course['image'])
        
        # Calculate completion percentage
        if current_user.is_authenticated:
            completions = SectionCompletion.query.filter_by(
                user_id=current_user.id,
                course_id=course_id
            ).all()
            completed_sections = {c.section_id for c in completions}
            total_sections = len(course['sections'])
            course['completion'] = round((len(completed_sections) / total_sections) * 100)
            course['completed_sections'] = completed_sections

    # Get section content
    section_path = os.path.join(course_path, 'sections', section_id)
    content_file = os.path.join(section_path, 'content.md')
    
    with open(content_file, 'r') as f:
        content = f.read()
        # Use our custom parser instead of plain markdown
        html_content = parse_section_content_markdown(content)

    # Get section index for navigation
    current_index = course['sections'].index(section_id)
    prev_section = course['sections'][current_index - 1] if current_index > 0 else None
    next_section = course['sections'][current_index + 1] if current_index < len(course['sections']) - 1 else None

    if init_failed:
        flash(f"""
            {init_error}. Some features might not work as expected.
        """, 'warning')

    return render_template('courses/section.html',
                         course=course,
                         section_id=section_id,
                         content=html_content,
                         prev_section=prev_section,
                         next_section=next_section,
                         init_failed=init_failed,
                         is_completed=is_completed)


def get_courses():
    """
    Scan courses directory and return list of course information
    """
    courses = []
    courses_dir = os.path.dirname(__file__)
    
    # Skip these directories during scanning
    skip_dirs = {'__pycache__', 'static', 'templates'}
    
    for course in os.listdir(courses_dir):
        if course in skip_dirs or course.startswith('.'):
            continue
            
        course_path = os.path.join(courses_dir, course)
        if not os.path.isdir(course_path):
            continue
            
        # Look for course.json
        course_json = os.path.join(course_path, 'course.json')
        if os.path.exists(course_json):
            with open(course_json) as f:
                course_data = json.load(f)
                course_data['id'] = course  # Add course directory as id
                
                # Use the course-specific media route for images
                if 'image' in course_data:
                    course_data['image'] = url_for('courses.serve_media', 
                                                 course_id=course, 
                                                 filename=course_data['image'])
                
                courses.append(course_data)
    
    return courses


def parse_section_content_markdown(content):
    """Parse markdown content with validation directives"""
    import re
    import markdown
    from flask import url_for

    # First handle Mermaid diagrams - convert them to pre class="mermaid"
    def replace_mermaid(match):
        diagram_content = match.group(1).strip()
        return f'<pre class="mermaid">{diagram_content}</pre>'

    # Replace ```mermaid blocks with proper mermaid pre tags
    content = re.sub(
        r'```mermaid\s*(.*?)\s*```',
        replace_mermaid,
        content,
        flags=re.DOTALL
    )

    # Process regular markdown
    md = markdown.Markdown(extensions=['extra', 'nl2br', 'sane_lists'])
    return md.convert(content)

def parse_markdown(content):
    extensions = [
        'extra',
        'codehilite',
        'tables',
        'toc',
        'pymdownx.arithmatex',
        'nl2br',
        'sane_lists',
        'fenced_code'
    ]

    extension_configs = {
        'codehilite': {
            'css_class': 'highlight',
            'linenums': True
        },
        'toc': {
            'permalink': True
        }
    }

    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs
    )

    # Convert markdown to HTML
    html = md.convert(content)
    return html