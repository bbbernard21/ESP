from app import create_app, db
from app.models.communication import GroupChat, ChatParticipant, ChatMessage
from app.models.user import User
from datetime import datetime

def seed_test_messages():
    # Get some users
    student1 = User.query.filter_by(username='student1').first()
    student2 = User.query.filter_by(username='student2').first()
    professor = User.query.filter_by(role='PROFESSOR').first()
    
    if not all([student1, student2, professor]):
        print("Error: Required users not found")
        return
    
    # Create a direct chat between student1 and student2
    direct_chat = GroupChat(created_by=student1)
    db.session.add(direct_chat)
    db.session.flush()
    
    # Add participants
    participant1 = ChatParticipant(chat=direct_chat, user=student1)
    participant2 = ChatParticipant(chat=direct_chat, user=student2)
    db.session.add_all([participant1, participant2])
    
    # Add some messages
    messages = [
        ChatMessage(chat=direct_chat, sender=student1, body="Hey! How are you?"),
        ChatMessage(chat=direct_chat, sender=student2, body="I'm good, thanks! How about you?"),
        ChatMessage(chat=direct_chat, sender=student1, body="Great! Did you finish the assignment?"),
        ChatMessage(chat=direct_chat, sender=student2, body="Not yet, working on it now.")
    ]
    db.session.add_all(messages)
    
    # Create a group chat
    group_chat = GroupChat(
        name="Data Structures Study Group",
        is_group=True,
        created_by=student1
    )
    db.session.add(group_chat)
    db.session.flush()
    
    # Add participants to group
    group_participants = [
        ChatParticipant(chat=group_chat, user=student1, is_admin=True),
        ChatParticipant(chat=group_chat, user=student2),
        ChatParticipant(chat=group_chat, user=professor)
    ]
    db.session.add_all(group_participants)
    
    # Add group messages
    group_messages = [
        ChatMessage(chat=group_chat, sender=student1, body="Welcome to the Data Structures study group!"),
        ChatMessage(chat=group_chat, sender=professor, body="Thanks for creating this group. Let me know if you have any questions."),
        ChatMessage(chat=group_chat, sender=student2, body="Great idea! I have a question about binary trees."),
        ChatMessage(chat=group_chat, sender=professor, body="Sure, what would you like to know?")
    ]
    db.session.add_all(group_messages)
    
    # Create a chat between student1 and professor
    prof_chat = GroupChat(created_by=student1)
    db.session.add(prof_chat)
    db.session.flush()
    
    # Add participants
    prof_participant1 = ChatParticipant(chat=prof_chat, user=student1)
    prof_participant2 = ChatParticipant(chat=prof_chat, user=professor)
    db.session.add_all([prof_participant1, prof_participant2])
    
    # Add messages
    prof_messages = [
        ChatMessage(chat=prof_chat, sender=student1, body="Hello Professor, I have a question about the midterm."),
        ChatMessage(chat=prof_chat, sender=professor, body="Of course, what would you like to know?"),
        ChatMessage(chat=prof_chat, sender=student1, body="Will it cover the recent topics on graph algorithms?"),
        ChatMessage(chat=prof_chat, sender=professor, body="Yes, focus on DFS, BFS, and shortest path algorithms.")
    ]
    db.session.add_all(prof_messages)
    
    try:
        db.session.commit()
        print("Test messages created successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating test messages: {e}")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_test_messages() 