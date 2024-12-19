from app import db
from datetime import datetime

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    read_timestamp = db.Column(db.DateTime)

    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_timestamp = datetime.utcnow()

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text)
    category = db.Column(db.String(20))  # academic, administrative, etc.
    priority = db.Column(db.String(20), default='normal')  # low, normal, high
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = datetime.utcnow()

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    course = db.relationship('Course', backref='discussions', lazy='joined')
    creator = db.relationship('User', backref='created_discussions', lazy='joined')
    posts = db.relationship('DiscussionPost', backref='discussion', lazy='dynamic', cascade='all, delete-orphan')

class DiscussionPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('discussion_post.id'))
    
    # Relationships
    user = db.relationship('User', backref='discussion_posts', lazy='joined')
    replies = db.relationship('DiscussionPost', backref=db.backref('parent', remote_side=[id]),
                            lazy='dynamic', cascade='all, delete-orphan')