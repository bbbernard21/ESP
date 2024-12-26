from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from app.models.user import UserRole

def get_dashboard_url(user):
    """Return the appropriate dashboard URL based on user role."""
    if user.is_admin:
        return url_for('admin.dashboard')
    elif user.is_professor:
        return url_for('professor.dashboard')
    else:  # student
        return url_for('student.dashboard')

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not any(current_user.has_role(role) for role in roles):
                flash('You do not have permission to access this page.', 'error')
                return redirect(get_dashboard_url(current_user))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(get_dashboard_url(current_user))
        return f(*args, **kwargs)
    return decorated_function

def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_professor:
            flash('You do not have permission to access this page.', 'error')
            return redirect(get_dashboard_url(current_user))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student:
            flash('You do not have permission to access this page.', 'error')
            return redirect(get_dashboard_url(current_user))
        return f(*args, **kwargs)
    return decorated_function

def admin_or_professor_required(f):
    return role_required(UserRole.ADMIN, UserRole.PROFESSOR)(f) 