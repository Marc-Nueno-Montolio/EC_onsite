from flask import render_template
from app.main import main_bp

from app.admin.routes import execute_vm_command

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/home')
def home():
    # Example usage
    success, output = execute_vm_command(1, "kubectl version --client")
    if success:
        print("Command output:", output)
    else:
        print("Error:", output)
    return render_template('home.html') 



