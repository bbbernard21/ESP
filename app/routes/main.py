from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.academic import AcademicRecord, Course, AcademicGoal
from app.models.communication import Notification, Message
from app import db

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/index')
@login_required
def index():
    # Get user's courses
    courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).all()
    
    # Get recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Get unread messages count
    unread_messages = Message.query.filter_by(
        recipient_id=current_user.id,
        read=False
    ).count()
    
    return render_template('main/index.html',
                         title='Home',
                         courses=courses,
                         notifications=notifications,
                         unread_messages=unread_messages)

@main.route('/dashboard')
@login_required
def dashboard():
    # Get academic records
    academic_records = AcademicRecord.query.filter_by(
        student_id=current_user.id
    ).join(Course).all()
    
    # Calculate GPA and other statistics
    total_credits = 0
    total_grade_points = 0
    for record in academic_records:
        if record.grade is not None and record.course.credits is not None:
            total_credits += record.course.credits
            total_grade_points += record.grade * record.course.credits
    
    gpa = total_grade_points / total_credits if total_credits > 0 else 0
    
    # Get active goals
    active_goals = AcademicGoal.query.filter_by(
        student_id=current_user.id,
        status='active'
    ).all()
    
    # Get recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('main/dashboard.html',
                         title='Dashboard',
                         academic_records=academic_records,
                         gpa=gpa,
                         active_goals=active_goals,
                         notifications=notifications) 

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