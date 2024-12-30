from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
from app.models.communication import Message, ChatMessage, ChatMessageRead, ChatParticipant
from app.models.communication import Notification

class UserRole(Enum):
    STUDENT = 'STUDENT'
    PROFESSOR = 'PROFESSOR'
    ADMIN = 'ADMIN'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), nullable=False, default=UserRole.STUDENT.value)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    program = db.relationship('Program', backref='students', lazy='joined')
    academic_records = db.relationship('AcademicRecord', backref='student', lazy='dynamic')
    academic_goals = db.relationship('AcademicGoal', backref='student', lazy='dynamic')
    notifications = db.relationship('Notification', backref='notification_user', lazy='dynamic', overlaps="user")
    
    # Message relationships
    sent_messages = db.relationship('Message', 
                                  foreign_keys='Message.sender_id',
                                  backref=db.backref('message_sender', lazy='joined'),
                                  lazy='dynamic',
                                  overlaps="sender,messages_sent")
    received_messages = db.relationship('Message',
                                      foreign_keys='Message.recipient_id',
                                      backref=db.backref('message_recipient', lazy='joined'),
                                      lazy='dynamic',
                                      overlaps="recipient,messages_received")
    
    # Chat relationships
    chats = db.relationship('ChatParticipant', backref='participant', lazy='dynamic')
    sent_chat_messages = db.relationship('ChatMessage',
                                       foreign_keys='ChatMessage.sender_id',
                                       backref=db.backref('chat_message_sender', lazy='joined'),
                                       lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def user_role(self):
        """Return the UserRole enum object for this user's role"""
        return UserRole(self.role.upper())
    
    @property
    def is_admin(self):
        return self.user_role == UserRole.ADMIN
    
    @property
    def is_professor(self):
        return self.user_role == UserRole.PROFESSOR
    
    @property
    def is_student(self):
        return self.user_role == UserRole.STUDENT
    
    def has_role(self, role):
        if isinstance(role, UserRole):
            return self.user_role == role
        return self.role.upper() == role.upper()
    
    # Admin capabilities
    def can_manage_users(self):
        return self.is_admin
    
    def can_manage_courses(self):
        return self.is_admin
    
    def can_manage_programs(self):
        return self.is_admin
    
    def can_view_analytics(self):
        return self.is_admin or self.is_professor
    
    # Professor capabilities
    def can_grade_students(self):
        return self.is_professor or self.is_admin
    
    def can_manage_course_content(self, course):
        if self.is_admin:
            return True
        return self.is_professor and course.professor_id == self.id
    
    def can_view_student_progress(self, student):
        if self.is_admin:
            return True
        if self.is_professor:
            # Check if student is enrolled in any of professor's courses
            return bool(student.academic_records.join(Course).filter(Course.professor_id == self.id).first())
        return self.id == student.id
    
    # Student capabilities
    def can_view_course(self, course):
        if self.is_admin or self.is_professor:
            return True
        return bool(self.academic_records.filter_by(course_id=course.id).first())
    
    def can_submit_assignment(self, assignment):
        if not self.is_student:
            return False
        # Check if student is enrolled in the course and assignment is still open
        course = assignment.course
        academic_record = self.academic_records.filter_by(course_id=course.id).first()
        if not academic_record:
            return False
        return datetime.utcnow() <= assignment.due_date
    
    # Notification methods
    def get_unread_notifications_count(self):
        """Return the count of unread notifications for the user"""
        return self.notifications.filter_by(read=False).count()
    
    def get_unread_messages_count(self):
        from app.models.communication import ChatMessage, ChatMessageRead, ChatParticipant, Message
        
        # Count unread direct messages
        direct_unread = Message.query.filter_by(
            recipient_id=self.id,
            read=False
        ).count()
        
        # Count unread group messages
        group_unread = (ChatMessage.query
            .join(ChatParticipant, ChatMessage.chat_id == ChatParticipant.chat_id)
            .outerjoin(ChatMessageRead, 
                (ChatMessageRead.message_id == ChatMessage.id) & 
                (ChatMessageRead.user_id == self.id))
            .filter(
                ChatParticipant.user_id == self.id,
                ChatMessage.sender_id != self.id,
                ChatMessageRead.id.is_(None)
            ).count())
        
        return direct_unread + group_unread
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id)) 