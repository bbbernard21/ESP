from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.academic import AcademicRecord, Course, AcademicGoal
from app.models.communication import Notification, Message
from app import db

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/index')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_professor:
        return redirect(url_for('professor.dashboard'))
    else:  # student
        return redirect(url_for('student.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    """Redirect to appropriate dashboard based on user role."""
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_professor:
        return redirect(url_for('professor.dashboard'))
    else:  # student
        return redirect(url_for('student.dashboard'))

@main.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html', title='My Profile')

@main.route('/settings')
@login_required
def settings():
    return render_template('main/settings.html', title='Settings')

@main.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        current_user.first_name = request.form['first_name']
        current_user.last_name = request.form['last_name']
        current_user.email = request.form['email']
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating your profile.', 'error')
    return redirect(url_for('main.profile'))

@main.route('/update_account_settings', methods=['POST'])
@login_required
def update_account_settings():
    try:
        current_user.username = request.form['username']
        # Add timezone handling here if needed
        db.session.commit()
        flash('Account settings updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating your account settings.', 'error')
    return redirect(url_for('main.settings'))

@main.route('/update_notification_settings', methods=['POST'])
@login_required
def update_notification_settings():
    try:
        # Update notification preferences in the database
        flash('Notification preferences updated successfully!', 'success')
    except Exception as e:
        flash('An error occurred while updating your notification preferences.', 'error')
    return redirect(url_for('main.settings'))

@main.route('/update_privacy_settings', methods=['POST'])
@login_required
def update_privacy_settings():
    try:
        # Update privacy settings in the database
        flash('Privacy settings updated successfully!', 'success')
    except Exception as e:
        flash('An error occurred while updating your privacy settings.', 'error')
    return redirect(url_for('main.settings'))

@main.route('/update_password', methods=['POST'])
@login_required
def update_password():
    try:
        if not current_user.check_password(request.form['current_password']):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('main.settings'))
        
        if request.form['new_password'] != request.form['confirm_password']:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('main.settings'))
        
        current_user.set_password(request.form['new_password'])
        db.session.commit()
        flash('Password updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating your password.', 'error')
    return redirect(url_for('main.settings')) 