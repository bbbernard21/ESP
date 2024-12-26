from app import db
from datetime import datetime
from app.models.user import User

class Program(db.Model):
    __tablename__ = 'programs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)  # in semesters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = db.relationship('Course', backref='program', lazy='dynamic')

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    semester = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active')  # active, inactive, archived
    
    # Relationships
    professor = db.relationship('User', backref='courses_teaching', foreign_keys=[professor_id])
    academic_records = db.relationship('AcademicRecord', backref='course', lazy='dynamic')
    materials = db.relationship('CourseMaterial', backref='course', lazy='dynamic')
    assignments = db.relationship('Assignment', backref='course', lazy='dynamic')
    exams = db.relationship('Exam', backref='course', lazy='dynamic')
    
    # Grade distribution
    assignments_weight = db.Column(db.Float, default=40.0)  # Default 40% for assignments
    midterm_weight = db.Column(db.Float, default=25.0)     # Default 25% for midterm
    final_weight = db.Column(db.Float, default=35.0)       # Default 35% for final exam

class AcademicRecord(db.Model):
    __tablename__ = 'academic_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    grade = db.Column(db.Float)
    status = db.Column(db.String(20), default='enrolled')  # enrolled, completed, dropped
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime)
    semester = db.Column(db.String(20))  # Fall, Spring, Summer
    academic_year = db.Column(db.String(20))  # e.g., "2023-2024"

class AcademicGoal(db.Model):
    __tablename__ = 'academic_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    target_grade = db.Column(db.Float)
    target_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='academic_goals', lazy='joined')

class CourseMaterial(db.Model):
    __tablename__ = 'course_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    material_type = db.Column(db.String(50))  # lecture, assignment, reading, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=False)
    total_points = db.Column(db.Float, default=100.0)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submission_file = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='submitted')  # submitted, graded
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime)
    
    # Relationships
    assignment = db.relationship('Assignment', backref='submissions')
    student = db.relationship('User', backref='assignment_submissions')
    
    def is_late(self):
        return self.submitted_at > self.assignment.due_date if self.submitted_at else False

class Exam(db.Model):
    __tablename__ = 'exams'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    exam_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)  # in minutes
    total_points = db.Column(db.Float, default=100.0)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamGrade(db.Model):
    __tablename__ = 'exam_grades'
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    exam = db.relationship('Exam', backref=db.backref('exam_grades', lazy='dynamic'))
    student = db.relationship('User', backref='exam_grades')

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    total_marks = db.Column(db.Float, default=100.0)
    duration = db.Column(db.Integer)  # in minutes
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='quizzes')
    submissions = db.relationship('QuizSubmission', backref='quiz', lazy='dynamic')

class QuizSubmission(db.Model):
    __tablename__ = 'quiz_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Float)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='submitted')  # submitted, graded
    feedback = db.Column(db.Text)
    
    # Relationships
    student = db.relationship('User', backref='quiz_submissions') 