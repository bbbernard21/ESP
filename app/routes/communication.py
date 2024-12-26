from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.communication import Message, Notification, Discussion, DiscussionPost
from app.models.user import User
from app.models.academic import Course, AcademicRecord
from datetime import datetime

communication = Blueprint('communication', __name__)

@communication.route('/messages')
@login_required
def messages():
    messages_received = Message.query.filter_by(
        recipient_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()
    
    messages_sent = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()
    
    return render_template('communication/messages.html',
                         title='Messages',
                         messages_received=messages_received,
                         messages_sent=messages_sent)

@communication.route('/send_message', methods=['POST'])
@login_required
def send_message():
    recipient = User.query.filter_by(username=request.form['recipient']).first()
    if recipient is None:
        flash('User not found.', 'error')
        return redirect(url_for('communication.messages'))
    
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        body=request.form['message']
    )
    db.session.add(message)
    
    # Create notification for recipient
    notification = Notification(
        user_id=recipient.id,
        title='New Message',
        body=f'You have a new message from {current_user.username}',
        category='communication'
    )
    db.session.add(notification)
    
    db.session.commit()
    flash('Your message has been sent.', 'success')
    return redirect(url_for('communication.messages'))

@communication.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()
    return render_template('communication/notifications.html',
                         title='Notifications',
                         notifications=notifications)

@communication.route('/mark_notification_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    notification.mark_as_read()
    db.session.commit()
    return jsonify({'success': True})

@communication.route('/mark_all_notifications_read')
@login_required
def mark_all_notifications_read():
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).all()
    
    for notification in notifications:
        notification.mark_as_read()
    
    db.session.commit()
    return jsonify({'success': True})

@communication.route('/discussions/<int:course_id>')
@login_required
def course_discussions(course_id):
    course = Course.query.get_or_404(course_id)
    # Verify user is enrolled in the course
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first_or_404()
    
    discussions = Discussion.query.filter_by(course_id=course_id)\
        .order_by(Discussion.created_at.desc()).all()
    
    return render_template('communication/discussions.html',
                         title='Course Discussions',
                         discussions=discussions,
                         course=course,
                         course_id=course_id)

@communication.route('/discussion/<int:discussion_id>')
@login_required
def discussion_detail(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    # Verify user is enrolled in the course
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=discussion.course_id
    ).first_or_404()
    
    # Get main posts (no parent) with their replies
    posts = DiscussionPost.query.filter_by(
        discussion_id=discussion_id,
        parent_id=None
    ).order_by(DiscussionPost.created_at.asc()).all()
    
    return render_template('communication/discussion_detail.html',
                         title=discussion.title,
                         discussion=discussion,
                         posts=posts)

@communication.route('/discussion/<int:discussion_id>/post', methods=['POST'])
@login_required
def add_post(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    # Verify user is enrolled in the course
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=discussion.course_id
    ).first_or_404()
    
    try:
        post = DiscussionPost(
            discussion_id=discussion_id,
            user_id=current_user.id,
            content=request.form['content'],
            parent_id=request.form.get('parent_id')
        )
        db.session.add(post)
        
        # Create notification for discussion starter if it's not their own post
        if discussion.created_by != current_user.id:
            notification = Notification(
                user_id=discussion.created_by,
                title='New Discussion Reply',
                body=f'New reply in your discussion: {discussion.title}',
                category='discussion'
            )
            db.session.add(notification)
        
        db.session.commit()
        flash('Your reply has been posted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while posting your reply.', 'error')
    
    return redirect(url_for('communication.discussion_detail', discussion_id=discussion_id))

@communication.route('/discussion/create/<int:course_id>', methods=['POST'])
@login_required
def create_discussion(course_id):
    # Verify user is enrolled in the course
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first_or_404()
    
    try:
        discussion = Discussion(
            title=request.form['title'],
            course_id=course_id,
            created_by=current_user.id
        )
        db.session.add(discussion)
        db.session.commit()
        
        # Create initial post
        post = DiscussionPost(
            discussion_id=discussion.id,
            user_id=current_user.id,
            content=request.form['content']
        )
        db.session.add(post)
        db.session.commit()
        
        flash('Discussion created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while creating the discussion.', 'error')
    
    return redirect(url_for('communication.discussion_detail', discussion_id=discussion.id)) 