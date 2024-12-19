from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), nullable=False, default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    academic_records = db.relationship('AcademicRecord', backref='student', lazy='dynamic')
    academic_goals = db.relationship('AcademicGoal', backref='student', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    messages_sent = db.relationship('Message',
                                  foreign_keys='Message.sender_id',
                                  backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message',
                                      foreign_keys='Message.recipient_id',
                                      backref='recipient', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_unread_notifications_count(self):
        return self.notifications.filter_by(read=False).count()

    def get_unread_messages_count(self):
        return self.messages_received.filter_by(read=False).count() 