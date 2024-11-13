from flask import render_template, redirect, url_for, request, flash, jsonify
from app.courses import courses_bp as bp
import os, json, markdown
import importlib
import inspect
from flask_login import current_user, login_required
from app.models import SectionCompletion, User
from app.database import db

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

    # Updated image pattern to handle both syntaxes
    image_pattern = r'!\[(.*?)\]\((.*?)\)(?:\{width=(\d+%)\})?|!\[(.*?)\]\((.*?)\s+"(\d+%?)"\)'

    def image_replacer(match):
        # Handle curly brace syntax
        if match.group(1) is not None:
            alt_text = match.group(1)
            image_path = match.group(2)
            size_spec = match.group(3) if match.group(3) else 'medium'
        # Handle quoted syntax
        else:
            alt_text = match.group(4)
            image_path = match.group(5)
            size_spec = match.group(6) if match.group(6) else 'medium'
        
        course_id = request.view_args.get('course_id')
        media_url = url_for('courses.serve_media', 
                          course_id=course_id, 
                          filename=image_path)
        
        # Enhanced size handling
        if isinstance(size_spec, str):
            if size_spec.endswith('%'):
                # Handle percentage values
                style = f'width: {size_spec};'
            elif size_spec.endswith('px'):
                # Handle pixel values
                style = f'width: {size_spec};'
            else:
                # Default size classes
                size_classes = {
                    'small': 'width: 200px;',
                    'medium': 'width: 400px;',
                    'big': 'width: 800px;'
                }
                style = size_classes.get(size_spec.lower(), size_classes['medium'])
        
        return f'<img src="{media_url}" alt="{alt_text}" style="{style}" class="img-fluid">'

    # Replace image paths before splitting into blocks
    content = re.sub(image_pattern, image_replacer, content)

    # Add fenced code block pattern
    code_pattern = r'```(\w+)?\n(.*?)```'
    
    def code_block_replacer(match):
        language = match.group(1) or 'text'
        code_content = match.group(2).strip()
        
        return f'''
        <div class="code-editor mb-3" data-language="{language}">
            <div class="code-editor-header d-flex justify-content-between align-items-center p-2">
                <span class="language-label">{language}</span>
                <button class="btn btn-sm btn-outline-light copy-btn">
                    <i class="bi bi-clipboard"></i>
                </button>
            </div>
            <div class="code-content" style="height: 200px;">{code_content}</div>
        </div>
        '''

    # Replace code blocks before other markdown processing
    content = re.sub(code_pattern, code_block_replacer, content, flags=re.DOTALL)

    # Configure markdown with extensions for proper list handling
    md = markdown.Markdown(extensions=[
        'extra',
        'nl2br',
        'sane_lists'  # Add this extension for better list handling
    ])
    
    # Pre-process content to fix list formatting
    def fix_list_formatting(content):
        lines = content.split('\n')
        result = []
        in_list = False
        
        for line in lines:
            # Check if line starts with number and period
            if re.match(r'^\d+\.', line.strip()):
                in_list = True
                # Ensure proper indentation for nested lists
                if line.startswith('    ') and result and result[-1].strip():
                    result.append(line)
                else:
                    result.append(line.strip())
            else:
                if in_list and line.strip() and not line.startswith('    '):
                    in_list = False
                result.append(line)
                
        return '\n'.join(result)

    # Pre-process content
    content = fix_list_formatting(content)

    # Split content into blocks
    blocks = re.split(r'\n\n+', content)
    html_parts = []
    
    for block in blocks:
        block = block.strip()
        if block.startswith('@validate'):
            # Parse validation directive
            lines = block.split('\n')
            directive = lines[0]
            
            # Extract validation parameters
            params = re.match(r'@validate\(type="([^"]+)", id="([^"]+)"\)', directive)
            if not params:
                continue
                
            input_type = params.group(1)
            validate_id = params.group(2)
            
            # Get question text (for action type, this is the button text)
            question = lines[1] if len(lines) > 1 else 'Validate'
            
            # Get options (lines starting with -)
            options = [line[1:].strip() for line in lines[2:] if line.strip().startswith('-')]
            
            # Generate HTML based on input type
            if input_type == "action":
                html = f'''
                <div class="mb-3">
                    <button id="btn-{validate_id}" class="btn btn-primary" onclick="validateAnswer('{validate_id}', 'action')">
                        {question}
                    </button>
                    <div id="result-{validate_id}" class="mt-2"></div>
                </div>
                '''
                html_parts.append(html)
            elif input_type == "text-input":
                html = f'''
                <div class="card mb-3">
                    <div class="card-body">
                        <p class="card-text">{question}</p>
                        <div class="input-group">
                            <input type="text" class="form-control" data-validate-input="{validate_id}">
                            <button class="btn btn-primary" onclick="validateAnswer('{validate_id}', 'text')">
                                Check Answer
                            </button>
                        </div>
                        <div id="result-{validate_id}" class="mt-2"></div>
                    </div>
                </div>
                '''
                html_parts.append(html)
            elif input_type == "button":
                buttons = []
                for option in options:
                    buttons.append(f'''
                    <button class="btn btn-outline-primary me-2 mb-2" 
                            onclick="validateAnswer('{validate_id}', 'button', '{option}')">
                        {option}
                    </button>
                    ''')
                
                html = f'''
                <div class="card mb-3">
                    <div class="card-body">
                        <p class="card-text">{question}</p>
                        <div class="d-flex flex-wrap">
                            {"".join(buttons)}
                        </div>
                        <div id="result-{validate_id}" class="mt-2"></div>
                    </div>
                </div>
                '''
                html_parts.append(html)
        else:
            # Process non-validate blocks with markdown
            if block:
                html_parts.append(md.convert(block))
    
    return '\n'.join(html_parts)