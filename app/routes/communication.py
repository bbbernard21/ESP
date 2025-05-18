from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from app.models.communication import (
    Message, Conversation, Notification, Discussion, DiscussionPost,
    GroupChat, ChatParticipant, ChatMessage, ChatMessageRead, Attachment
)
from app.models.user import User, UserRole
from app import db, socketio

communication = Blueprint('communication', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'zip', 'rar', 'mp3', 'mp4'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_attachment(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create unique filename to prevent overwrites
        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
        
        # Create uploads directory inside static folder if it doesn't exist
        upload_dir = os.path.join('static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file path relative to static folder
        file_path = os.path.join('uploads', unique_filename)
        # Full path for saving the file
        full_path = os.path.join(current_app.root_path, 'static', file_path)
        
        # Save file
        file.save(full_path)
        
        return Attachment(
            filename=filename,
            file_path=file_path,  # Store relative path
            file_type=file.content_type,
            file_size=os.path.getsize(full_path)
        )
    return None

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
    
    # All users except current user and admins for new message modal
    available_users = User.query.filter(User.id != current_user.id, User.role != UserRole.ADMIN.value).all()
    
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
        
        message_list = [{
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.first_name,
            'body': msg.body,
            'content_type': msg.content_type,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'read': msg.read,
            'attachments': [{
                'id': att.id,
                'filename': att.filename,
                'file_path': att.file_path,
                'file_type': att.file_type
            } for att in msg.attachments]
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
            'content_type': msg.content_type,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'read_by': [read.user_id for read in msg.read_by],
            'attachments': [{
                'id': att.id,
                'filename': att.filename,
                'file_path': att.file_path,
                'file_type': att.file_type
            } for att in msg.attachments]
        } for msg in messages]
    })

@communication.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    chat_id = request.form.get('chat_id')
    content = request.form.get('content')
    content_type = request.form.get('content_type', 'text')
    
    print("Received message request:")
    print(f"chat_id: {chat_id}")
    print(f"content: {content}")
    print(f"content_type: {content_type}")
    print(f"Files in request: {request.files}")
    
    if not chat_id or not content:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Handle direct conversation
        conversation = Conversation.query.get(chat_id)
        if conversation:
            if current_user.id not in [conversation.user1_id, conversation.user2_id]:
                return jsonify({'error': 'Unauthorized'}), 403
            
            recipient_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
            
            message = Message(
                conversation_id=chat_id,
                sender_id=current_user.id,
                recipient_id=recipient_id,
                body=content,
                content_type=content_type,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            
            # Handle attachments
            files = request.files.getlist('attachments[]')
            print(f"Processing {len(files)} files")
            
            for file in files:
                print(f"Processing file: {file.filename}, type: {file.content_type}")
                attachment = save_attachment(file)
                if attachment:
                    print(f"Created attachment: {attachment.filename}, path: {attachment.file_path}")
                    attachment.message = message
                    db.session.add(attachment)
                else:
                    print(f"Failed to create attachment for file: {file.filename}")
            
            conversation.updated_at = datetime.utcnow()
            
            notification = Notification(
                user_id=recipient_id,
                title="New Message",
                body=f"New message from {current_user.first_name}",
                category="message"
            )
            db.session.add(notification)
            
            db.session.commit()
            
            # Emit new message event to recipient(s)
            socketio.emit('new_message', {
                'conversation_id': conversation.id,
                'sender_id': message.sender_id,
                'sender_name': current_user.first_name,
                'body': message.body,
                'content_type': message.content_type,
                'timestamp': message.timestamp.strftime('%H:%M'),
                'attachments': [{
                    'id': att.id,
                    'filename': att.filename,
                    'file_path': att.file_path,
                    'file_type': att.file_type
                } for att in message.attachments]
            }, room=str(recipient_id))
            
            # Emit new notification event to recipient
            socketio.emit('new_notification', {
                'notification_id': notification.id,
                'title': notification.title,
                'body': notification.body,
                'category': notification.category
            }, room=str(recipient_id))
            
            # Verify attachments after commit
            message = Message.query.get(message.id)
            print(f"Message attachments after commit: {[att.filename for att in message.attachments]}")
            
            return jsonify({
                'success': True,
                'message': {
                    'id': message.id,
                    'sender_id': message.sender_id,
                    'sender_name': current_user.first_name,
                    'body': message.body,
                    'content_type': message.content_type,
                    'timestamp': message.timestamp.strftime('%H:%M'),
                    'read': False,
                    'attachments': [{
                        'id': att.id,
                        'filename': att.filename,
                        'file_path': att.file_path,
                        'file_type': att.file_type
                    } for att in message.attachments]
                }
            })
            
        # Handle group chat
        group_chat = GroupChat.query.get(chat_id)
        if group_chat:
            # Check if user is participant
            participant = ChatParticipant.query.filter_by(
                chat_id=chat_id,
                user_id=current_user.id
            ).first_or_404()
            
            message = ChatMessage(
                chat_id=chat_id,
                sender_id=current_user.id,
                body=content,
                content_type=content_type
            )
            db.session.add(message)
            
            # Handle attachments
            files = request.files.getlist('attachments[]')
            for file in files:
                attachment = save_attachment(file)
                if attachment:
                    attachment.chat_message = message
                    db.session.add(attachment)
            
            db.session.commit()
            
            # Emit new message event to all participants except sender
            for participant in group_chat.participants:
                if participant.user_id != current_user.id:
                    # Create notification for group message
                    notification = Notification(
                        user_id=participant.user_id,
                        title="New Group Message",
                        body=f"New message in group '{group_chat.name}' from {current_user.first_name}",
                        category="group_message"
                    )
                    db.session.add(notification)
                    db.session.commit()
                    socketio.emit('new_group_message', {
                        'chat_id': group_chat.id,
                        'sender_id': message.sender_id,
                        'sender_name': current_user.first_name,
                        'body': message.body,
                        'content_type': message.content_type,
                        'timestamp': message.timestamp.strftime('%H:%M'),
                        'attachments': [{
                            'id': att.id,
                            'filename': att.filename,
                            'file_path': att.file_path,
                            'file_type': att.file_type
                        } for att in message.attachments]
                    }, room=str(participant.user_id))
                    # Emit new notification event
                    socketio.emit('new_notification', {
                        'notification_id': notification.id,
                        'title': notification.title,
                        'body': notification.body,
                        'category': notification.category
                    }, room=str(participant.user_id))
            
            return jsonify({
                'success': True,
                'message': {
                    'id': message.id,
                    'sender_id': message.sender_id,
                    'sender_name': current_user.first_name,
                    'body': message.body,
                    'content_type': message.content_type,
                    'timestamp': message.timestamp.strftime('%H:%M'),
                    'attachments': [{
                        'id': att.id,
                        'filename': att.filename,
                        'file_path': att.file_path,
                        'file_type': att.file_type
                    } for att in message.attachments]
                }
            })
            
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

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
        # Emit real-time event to update notification badge
        socketio.emit('notification_read', {'notification_id': notification.id}, room=str(notification.user_id))
        return jsonify({'success': True})
    
    return jsonify({'error': 'Missing notification ID'}), 400

@communication.route('/api/notifications/unread_count')
@login_required
def unread_notification_count():
    count = current_user.get_unread_notifications_count()
    return jsonify({'unread_count': count})

@communication.route('/api/messages/direct/<int:conversation_id>/mark_read', methods=['POST'])
@login_required
def mark_direct_messages_read(conversation_id):
    from app.models.communication import Message, Conversation
    conversation = Conversation.query.get_or_404(conversation_id)
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    unread_msgs = Message.query.filter_by(conversation_id=conversation_id, recipient_id=current_user.id, read=False).all()
    for msg in unread_msgs:
        msg.read = True
        msg.read_at = datetime.utcnow()
    db.session.commit()
    # Emit real-time event to update message badge
    socketio.emit('message_read', {'chat_id': conversation_id}, room=str(current_user.id))
    return jsonify({'success': True})

@communication.route('/api/messages/group/<int:chat_id>/mark_read', methods=['POST'])
@login_required
def mark_group_messages_read(chat_id):
    from app.models.communication import ChatMessage, ChatMessageRead, ChatParticipant
    chat_participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not chat_participant:
        return jsonify({'error': 'Unauthorized'}), 403
    unread_msgs = (ChatMessage.query
        .filter(ChatMessage.chat_id == chat_id, ChatMessage.sender_id != current_user.id)
        .outerjoin(ChatMessageRead, (ChatMessageRead.message_id == ChatMessage.id) & (ChatMessageRead.user_id == current_user.id))
        .filter(ChatMessageRead.id.is_(None))
        .all())
    for msg in unread_msgs:
        read_entry = ChatMessageRead(user_id=current_user.id, message_id=msg.id)
        db.session.add(read_entry)
    db.session.commit()
    # Emit real-time event to update message badge
    socketio.emit('message_read', {'chat_id': chat_id}, room=str(current_user.id))
    return jsonify({'success': True})

@communication.route('/api/messages/unread_count')
@login_required
def unread_message_count():
    count = current_user.get_unread_messages_count()
    return jsonify({'unread_count': count})


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

@communication.route('/student/discussion/<int:discussion_id>/post', methods=['POST'])
@login_required
def add_discussion_post(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    content = request.form.get('content')
    content_type = request.form.get('content_type', 'text')
    parent_id = request.form.get('parent_id')
    
    if not content:
        flash('Post content is required.', 'error')
        return redirect(url_for('student.discussion_detail', discussion_id=discussion_id))
    
    try:
        post = DiscussionPost(
            content=content,
            content_type=content_type,
            discussion_id=discussion_id,
            author_id=current_user.id,
            parent_id=parent_id if parent_id else None
        )
        db.session.add(post)
        
        # Handle attachments
        files = request.files.getlist('attachments[]')
        for file in files:
            attachment = save_attachment(file)
            if attachment:
                attachment.discussion_post = post
                db.session.add(attachment)
        
        db.session.commit()
        flash('Your post has been added.', 'success')

        # Emit new notification event to all discussion participants except the author
        participant_ids = set(
            p.author_id for p in DiscussionPost.query.filter_by(discussion_id=discussion_id).all()
            if p.author_id != current_user.id
        )
        for user_id in participant_ids:
            notification = Notification(
                user_id=user_id,
                title="New Discussion Post",
                body=f"New post in discussion '{discussion.title}' by {current_user.first_name}",
                category="discussion"
            )
            db.session.add(notification)
            db.session.commit()
            socketio.emit('new_notification', {
                'notification_id': notification.id,
                'title': notification.title,
                'body': notification.body,
                'category': notification.category
            }, room=str(user_id))
        
    except Exception as e:
        db.session.rollback()
        flash('Error adding post. Please try again.', 'error')
        print(f"Error adding discussion post: {str(e)}")
    
    return redirect(url_for('student.discussion_detail', discussion_id=discussion_id)) 