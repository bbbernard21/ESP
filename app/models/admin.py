from app import db
from datetime import datetime

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    role = db.Column(db.String(50), default='admin')  # admin, super_admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='admin_profile')
    
    def __repr__(self):
        return f'<Admin {self.user.username}>'
    
    @property
    def is_super_admin(self):
        return self.role == 'super_admin' 