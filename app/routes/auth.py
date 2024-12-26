from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User, UserRole
from app import db
from werkzeug.urls import url_parse
from datetime import datetime

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url(current_user))
    
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user is None or not user.check_password(request.form['password']):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=request.form.get('remember_me'))
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = get_dashboard_url(user)
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In')

def get_dashboard_url(user):
    """Return the appropriate dashboard URL based on user role."""
    if user.is_admin:
        return url_for('admin.dashboard')
    elif user.is_professor:
        return url_for('professor.dashboard')
    else:  # student
        return url_for('student.dashboard')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url(current_user))
    
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            role=UserRole.STUDENT.value  # Default role for self-registration is student
        )
        user.set_password(request.form['password'])
        
        db.session.add(user)
        db.session.commit()
        
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register') 