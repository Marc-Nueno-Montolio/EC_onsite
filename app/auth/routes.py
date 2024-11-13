from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.auth import auth_bp
from app.models import User
from app.forms import LoginForm

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            # Redirect based on user role
            if user.is_admin:
                return redirect(url_for('admin.admin_dashboard'))
            else:
                return redirect(url_for('courses.list'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    
    # Redirect based on user role
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Implement registration logic here
    return render_template('register.html')
