from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.models.communication import (
    Message, Conversation, Notification, Discussion, DiscussionPost,
    GroupChat, ChatParticipant, ChatMessage, ChatMessageRead
)
from app.models.user import User, UserRole
from app import db

communication = Blueprint('communication', __name__)

@communication.route('/messages')
@login_required
def messages():
    # Debug user role information
    print(f"Current user: {current_user}")
    print(f"User role: {current_user.role}")
    
    # Get direct conversations
    direct_conversations = (Conversation.query
        .filter(
            (Conversation.user1_id == current_user.id) |
            (Conversation.user2_id == current_user.id)
        )
        .order_by(Conversation.updated_at.desc())
        .all())
    
    # Get group chats
    group_chats = (GroupChat.query
        .join(ChatParticipant)
        .filter(ChatParticipant.user_id == current_user.id)
        .order_by(GroupChat.created_at.desc())
        .all())
    
    # Get all users except current user for new message/group creation
    available_users = User.query.filter(User.id != current_user.id).all()
    
    # Determine which base template to use
    is_student = current_user.role == UserRole.STUDENT.value
    base_template = 'student/base.html' if is_student else 'base.html'
    print(f"Is student: {is_student}")
    print(f"Using template: {base_template}")
    
    return render_template('communication/messages.html',
                         direct_conversations=direct_conversations,
                         group_chats=group_chats,
                         available_users=available_users,
                         ChatMessageRead=ChatMessageRead,
                         base_template=base_template)

@communication.route('/api/messages/direct/<int:conversation_id>')
@login_required
def get_direct_messages(conversation_id):
    print(f"Getting messages for conversation: {conversation_id}")  # Debug log
    
    try:
        # Clear any stale data
        db.session.expire_all()
        
        conversation = Conversation.query.get_or_404(conversation_id)
        print(f"Found conversation between users: {conversation.user1_id} and {conversation.user2_id}")  # Debug log
        
        # Check if user is part of conversation
        if current_user.id not in [conversation.user1_id, conversation.user2_id]:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Mark messages as read
        unread_messages = Message.query.filter_by(
            conversation_id=conversation_id,
            recipient_id=current_user.id,
            read=False
        ).all()
        
        for message in unread_messages:
            message.read = True
            message.read_at = datetime.utcnow()
            
            # Also mark any notifications as read
            notification = Notification.query.filter_by(
                user_id=current_user.id,
                category='message',
                read=False
            ).first()
            if notification:
                notification.mark_as_read()
        
        db.session.commit()
        
        # Get messages for the conversation with a fresh query
        messages = (Message.query
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.timestamp.asc())  # Make sure messages are in chronological order
            .all())
        
        # Debug print
        print(f"Found {len(messages)} messages")  # Debug log
        print("Messages being sent:", [{"id": msg.id, "body": msg.body, "sender_id": msg.sender_id, "timestamp": msg.timestamp} for msg in messages])
        
        message_list = [{
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.first_name,
            'body': msg.body,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'read': msg.read
        } for msg in messages]
        
        print("Formatted messages:", message_list)  # Additional debug print
        
        return jsonify({
            'messages': message_list
        })
        
    except Exception as e:
        print(f"Error retrieving messages: {str(e)}")
        return jsonify({'error': 'Failed to retrieve messages'}), 500

@communication.route('/api/messages/group/<int:chat_id>')
@login_required
def get_group_messages(chat_id):
    chat = GroupChat.query.get_or_404(chat_id)
    
    # Check if user is participant
    participant = ChatParticipant.query.filter_by(
        chat_id=chat_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Mark messages as read
    unread_messages = (ChatMessage.query
        .join(ChatMessageRead, isouter=True)
        .filter(
            ChatMessage.chat_id == chat_id,
            ChatMessage.sender_id != current_user.id,
            ~ChatMessage.read_by.any(ChatMessageRead.user_id == current_user.id)
        ).all())
    
    for message in unread_messages:
        read_mark = ChatMessageRead(message=message, user=current_user)
        db.session.add(read_mark)
        
        # Also mark any notifications as read
        notification = Notification.query.filter_by(
            user_id=current_user.id,
            category='message',
            read=False
        ).first()
        if notification:
            notification.mark_as_read()
    
    db.session.commit()
    
    # Get messages for the chat
    messages = (ChatMessage.query
        .filter_by(chat_id=chat_id)
        .order_by(ChatMessage.timestamp)
        .all())
    
    return jsonify({
        'messages': [{
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.first_name,
            'body': msg.body,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'read_by': [read.user_id for read in msg.read_by]
        } for msg in messages]
    })

@communication.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    chat_id = data.get('chat_id')
    message_text = data.get('message')
    
    print(f"Sending message: chat_id={chat_id}, text={message_text}")  # Debug log
    
    if not chat_id or not message_text:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # First check if this is a direct conversation
        conversation = Conversation.query.get(chat_id)
        if conversation:
            print(f"Found direct conversation: {conversation.id}")  # Debug log
            
            if current_user.id not in [conversation.user1_id, conversation.user2_id]:
                return jsonify({'error': 'Unauthorized'}), 403
            
            recipient_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
            print(f"Recipient ID: {recipient_id}")  # Debug log
            
            message = Message(
                conversation_id=chat_id,
                sender_id=current_user.id,
                recipient_id=recipient_id,
                body=message_text,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            print(f"Created direct message object: {message.body}")  # Debug log
            
            conversation.updated_at = datetime.utcnow()
            
            notification = Notification(
                user_id=recipient_id,
                title="New Message",
                body=f"New message from {current_user.first_name}",
                category="message"
            )
            db.session.add(notification)
            
            db.session.commit()
            
            saved_message = Message.query.get(message.id)
            if saved_message:
                print(f"Successfully saved direct message with ID: {saved_message.id}, body: {saved_message.body}")
                
                conversation_messages = Message.query.filter_by(conversation_id=chat_id).all()
                print(f"All messages in conversation {chat_id}: {[(m.id, m.body) for m in conversation_messages]}")
                
                return jsonify({
                    'success': True,
                    'message': {
                        'id': saved_message.id,
                        'sender_id': saved_message.sender_id,
                        'sender_name': current_user.first_name,
                        'body': saved_message.body,
                        'timestamp': saved_message.timestamp.strftime('%H:%M'),
                        'read': False
                    }
                })
            else:
                print("Error: Direct message was not found after saving")
                return jsonify({'error': 'Message was not saved properly'}), 500
        
        # If not a direct conversation, check for group chat
        group_chat = GroupChat.query.get(chat_id)
        if group_chat:
            print(f"Found group chat: {group_chat.id}")  # Debug log
            
            # Check if user is participant
            participant = ChatParticipant.query.filter_by(
                chat_id=chat_id,
                user_id=current_user.id
            ).first_or_404()
            
            # Create and save new message
            message = ChatMessage(
                chat_id=chat_id,
                sender_id=current_user.id,
                body=message_text,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            print(f"Created group message object: {message.body}")  # Debug log
            
            # Create notifications for other participants
            for participant in group_chat.participants:
                if participant.user_id != current_user.id:
                    notification = Notification(
                        user_id=participant.user_id,
                        title="New Message",
                        body=f"New message from {current_user.first_name} in {group_chat.name or 'chat'}",
                        category="message"
                    )
                    db.session.add(notification)
            
            db.session.commit()
            
            saved_message = ChatMessage.query.get(message.id)
            if saved_message:
                print(f"Successfully saved group message with ID: {saved_message.id}, body: {saved_message.body}")
                return jsonify({
                    'success': True,
                    'message': {
                        'id': saved_message.id,
                        'sender_id': saved_message.sender_id,
                        'sender_name': current_user.first_name,
                        'body': saved_message.body,
                        'timestamp': saved_message.timestamp.strftime('%H:%M'),
                        'read_by': []
                    }
                })
            else:
                print("Error: Group message was not found after saving")
                return jsonify({'error': 'Message was not saved properly'}), 500
        
        # If we get here, neither conversation nor group chat was found
        print(f"Error: No conversation or group chat found with ID: {chat_id}")
        return jsonify({'error': 'Invalid chat ID'}), 404
                
    except Exception as e:
        print(f"Error saving message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save message'}), 500

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
    
    # Determine which base template to use
    is_student = current_user.role == UserRole.STUDENT.value
    base_template = 'student/base.html' if is_student else 'base.html'
    print(f"Is student: {is_student}")
    print(f"Using template: {base_template}")
    
    return render_template('communication/notifications.html', 
                         notifications=notifications,
                         base_template=base_template)

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

@communication.route('/group_chats')
@login_required
def group_chats():
    # Get all group chats where the user is a participant
    group_chats = (GroupChat.query
        .join(ChatParticipant)
        .filter(
            ChatParticipant.user_id == current_user.id,
            GroupChat.is_group == True
        )
        .order_by(GroupChat.created_at.desc())
        .all())
    
    return render_template('communication/group_chats.html', group_chats=group_chats)

@communication.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        name = request.form.get('name')
        participant_ids = request.form.getlist('participants')
        
        if not name or not participant_ids:
            flash('Please provide a group name and select at least one participant.', 'error')
            return redirect(url_for('communication.create_group'))
        
        # Create new group chat
        group = GroupChat(
            name=name,
            is_group=True,
            created_by_id=current_user.id
        )
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add creator as admin
        creator_participant = ChatParticipant(
            chat_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(creator_participant)
        
        # Add other participants
        for user_id in participant_ids:
            if int(user_id) != current_user.id:
                participant = ChatParticipant(
                    chat_id=group.id,
                    user_id=int(user_id)
                )
                db.session.add(participant)
        
        db.session.commit()
        flash('Group chat created successfully!', 'success')
        return redirect(url_for('communication.messages'))
    
    # Get all users except current user
    available_users = User.query.filter(User.id != current_user.id).all()
    return render_template('communication/create_group.html', available_users=available_users)

@communication.route('/group/<int:group_id>/settings', methods=['GET', 'POST'])
@login_required
def group_settings(group_id):
    group = GroupChat.query.get_or_404(group_id)
    participant = ChatParticipant.query.filter_by(
        chat_id=group_id,
        user_id=current_user.id,
        is_admin=True
    ).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            group.name = name
            db.session.commit()
            flash('Group settings updated successfully!', 'success')
        return redirect(url_for('communication.messages'))
    
    return render_template('communication/group_settings.html', group=group)

@communication.route('/group/<int:group_id>/participants', methods=['POST'])
@login_required
def manage_participants(group_id):
    group = GroupChat.query.get_or_404(group_id)
    participant = ChatParticipant.query.filter_by(
        chat_id=group_id,
        user_id=current_user.id,
        is_admin=True
    ).first_or_404()
    
    action = request.form.get('action')
    user_id = request.form.get('user_id')
    
    if not action or not user_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    target_participant = ChatParticipant.query.filter_by(
        chat_id=group_id,
        user_id=int(user_id)
    ).first()
    
    if action == 'remove':
        if target_participant:
            db.session.delete(target_participant)
            db.session.commit()
            return jsonify({'success': True})
    elif action == 'make_admin':
        if target_participant:
            target_participant.is_admin = True
            db.session.commit()
            return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid action'}), 400 