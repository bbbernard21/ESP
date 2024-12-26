from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.models.communication import Message, Conversation, Notification
from app.models.user import User
from app import db

communication = Blueprint('communication', __name__)

@communication.route('/messages')
@login_required
def messages():
    # Get all conversations for the current user
    conversations = Conversation.query.filter(
        (Conversation.user1_id == current_user.id) | 
        (Conversation.user2_id == current_user.id)
    ).all()
    
    # Process conversations to include last message and other user
    processed_conversations = []
    for conv in conversations:
        other_user = conv.user2 if conv.user1_id == current_user.id else conv.user1
        last_message = Message.query.filter_by(conversation_id=conv.id).order_by(Message.timestamp.desc()).first()
        unread_count = Message.query.filter_by(
            conversation_id=conv.id,
            recipient_id=current_user.id,
            read=False
        ).count()
        
        processed_conversations.append({
            'id': conv.id,
            'other_user': other_user,
            'last_message': last_message,
            'unread': unread_count > 0
        })
    
    return render_template('communication/messages.html', conversations=processed_conversations)

@communication.route('/api/messages/<int:conversation_id>')
@login_required
def get_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get other user
    other_user = conversation.user2 if conversation.user1_id == current_user.id else conversation.user1
    
    # Mark unread messages as read
    unread_messages = Message.query.filter_by(
        conversation_id=conversation_id,
        recipient_id=current_user.id,
        read=False
    ).all()
    
    for message in unread_messages:
        message.read = True
        message.read_timestamp = datetime.utcnow()
    
    db.session.commit()
    
    # Get messages
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    
    return jsonify({
        'recipient': other_user.username,
        'online': other_user.is_online(),  # You'll need to implement this method
        'messages': [{
            'id': msg.id,
            'sender_id': msg.sender_id,
            'body': msg.body,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'read': msg.read
        } for msg in messages]
    })

@communication.route('/api/messages/<int:conversation_id>/new')
@login_required
def get_new_messages(conversation_id):
    after = request.args.get('after')
    if after:
        after = datetime.strptime(after, '%Y-%m-%d %H:%M:%S')
        messages = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.timestamp > after
        ).order_by(Message.timestamp).all()
    else:
        messages = []
    
    return jsonify({
        'messages': [{
            'id': msg.id,
            'sender_id': msg.sender_id,
            'body': msg.body,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'read': msg.read
        } for msg in messages]
    })

@communication.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    
    conversation_id = data.get('conversation_id')
    message_text = data.get('message')
    
    if not conversation_id or not message_text:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Verify user is part of conversation
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Create and save new message
    recipient_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        body=message_text
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True, 'message_id': message.id})

@communication.route('/api/conversations/new', methods=['POST'])
@login_required
def start_conversation():
    data = request.get_json()
    recipient_username = data.get('recipient')
    message_text = data.get('message')
    
    if not recipient_username or not message_text:
        return jsonify({'error': 'Missing required fields'}), 400
    
    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if conversation already exists
    existing_conversation = Conversation.query.filter(
        ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == recipient.id)) |
        ((Conversation.user1_id == recipient.id) & (Conversation.user2_id == current_user.id))
    ).first()
    
    if existing_conversation:
        conversation_id = existing_conversation.id
    else:
        # Create new conversation
        conversation = Conversation(user1_id=current_user.id, user2_id=recipient.id)
        db.session.add(conversation)
        db.session.flush()  # Get the conversation ID
        conversation_id = conversation.id
    
    # Create and save new message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=recipient.id,
        body=message_text
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'conversation_id': conversation_id,
        'message_id': message.id
    })

@communication.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('communication/notifications.html', notifications=notifications)

@communication.route('/api/notifications/mark_read', methods=['POST'])
@login_required
def mark_notification_read():
    data = request.get_json()
    notification_id = data.get('notification_id')
    
    if notification_id:
        notification = Notification.query.get_or_404(notification_id)
        if notification.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        notification.mark_as_read()
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Missing notification ID'}), 400

@communication.route('/api/notifications/mark_all_read', methods=['POST'])
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