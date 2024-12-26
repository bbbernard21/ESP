from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
from app.models.communication import Message, Notification

class UserRole(Enum):
    ADMIN = 'admin'
    PROFESSOR = 'professor'
    STUDENT = 'student'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    role = db.Column(db.String(20), nullable=False, default=UserRole.STUDENT.value)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))  # For students
    
    # Relationships
    program = db.relationship('Program', backref='students', lazy='joined')
    academic_records = db.relationship('AcademicRecord', backref='student', lazy='dynamic')
    academic_goals = db.relationship('AcademicGoal', backref='student', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='notification_recipient', lazy='dynamic')
    
    # Message relationships
    sent_messages = db.relationship('Message', 
                                  foreign_keys='Message.sender_id',
                                  back_populates='message_sender',
                                  lazy='dynamic')
    received_messages = db.relationship('Message',
                                      foreign_keys='Message.recipient_id',
                                      back_populates='message_recipient',
                                      lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Role-based methods
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN.value

    @property
    def is_professor(self):
        return self.role == UserRole.PROFESSOR.value

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT.value

    def has_role(self, role):
        if isinstance(role, str):
            return self.role == role
        return self.role == role.value

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
        return self.notifications.filter(Notification.read_at == None).count()

    def get_unread_messages_count(self):
        """Return the count of unread messages for the user"""
        return self.received_messages.filter(Message.read_at == None).count()

    # Academic methods
    def get_current_courses(self):
        """Get currently enrolled courses for students or assigned courses for professors"""
        if self.is_student:
            return [record.course for record in self.academic_records.filter_by(status='enrolled')]
        elif self.is_professor:
            return Course.query.filter_by(professor_id=self.id).all()
        return Course.query.all()  # For admin

    def get_current_gpa(self):
        """Calculate current GPA for students"""
        if not self.is_student:
            return None
        
        completed_records = self.academic_records.filter_by(status='completed').all()
        if not completed_records:
            return 0.0
            
        total_credits = sum(record.course.credits for record in completed_records)
        weighted_grades = sum(record.grade * record.course.credits for record in completed_records)
        
        return weighted_grades / total_credits if total_credits > 0 else 0.0

    def get_semester_progress(self):
        """Get progress for current semester courses"""
        if not self.is_student:
            return {}
            
        progress = {}
        current_courses = self.get_current_courses()
        
        for course in current_courses:
            # Calculate completed assessment weight
            completed_weight = 0
            current_grade = 0
            
            # Add assignment grades
            for assignment in course.assignments:
                submission = assignment.submissions.filter_by(student_id=self.id).first()
                if submission and submission.grade:
                    weight = assignment.weight * (course.assignments_weight / 100)
                    completed_weight += weight
                    current_grade += (submission.grade * weight / 100)
            
            # Add exam grades
            for exam in course.exams:
                grade = exam.exam_grades.filter_by(student_id=self.id).first()
                if grade:
                    weight = course.midterm_weight if exam.exam_type == 'midterm' else course.final_weight
                    completed_weight += weight
                    current_grade += (grade.grade * weight / 100)
            
            progress[course.id] = {
                'completed_weight': completed_weight,
                'current_grade': current_grade,
                'remaining_weight': 100 - completed_weight
            }
        
        return progress

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id)) 