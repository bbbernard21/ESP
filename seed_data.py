from app import create_app, db
from app.models.user import User, UserRole
from app.models.academic import (
    Program, Course, AcademicRecord, AcademicGoal, 
    CourseMaterial, Assignment, AssignmentSubmission,
    Exam
)
from app.models.communication import (
    Message, Notification, Discussion, DiscussionPost,
    Announcement, Conversation
)
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def seed_database():
    # Create programs
    programs_data = [
        {
            'name': 'Computer Science',
            'code': 'CS',
            'description': 'Bachelor of Science in Computer Science'
        },
        {
            'name': 'Information Technology',
            'code': 'IT',
            'description': 'Bachelor of Science in Information Technology'
        }
    ]
    
    for program_data in programs_data:
        program = Program(**program_data)
        db.session.add(program)
    
    db.session.commit()
    
    # Create users
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'password_hash': generate_password_hash('admin123'),
            'first_name': 'Admin',
            'last_name': 'User',
            'role': UserRole.ADMIN,
            'is_active': True
        },
        {
            'username': 'professor1',
            'email': 'professor1@example.com',
            'password_hash': generate_password_hash('prof123'),
            'first_name': 'John',
            'last_name': 'Smith',
            'role': UserRole.PROFESSOR,
            'is_active': True
        },
        {
            'username': 'student1',
            'email': 'student1@example.com',
            'password_hash': generate_password_hash('student123'),
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'role': UserRole.STUDENT,
            'program_id': 1,
            'is_active': True
        }
    ]
    
    for user_data in users_data:
        user = User(**user_data)
        db.session.add(user)
    
    db.session.commit()
    
    # Create courses
    courses_data = [
        {
            'code': 'CS101',
            'name': 'Introduction to Programming',
            'description': 'Basic programming concepts using Python',
            'credits': 3,
            'professor_id': 2,  # professor1
            'program_id': 1,
            'semester': 'Fall',
            'assignments_weight': 40,
            'midterm_weight': 25,
            'final_weight': 35
        },
        {
            'code': 'CS102',
            'name': 'Data Structures',
            'description': 'Fundamental data structures and algorithms',
            'credits': 3,
            'professor_id': 2,  # professor1
            'program_id': 1,
            'semester': 'Fall',
            'assignments_weight': 40,
            'midterm_weight': 25,
            'final_weight': 35
        }
    ]
    
    for course_data in courses_data:
        course = Course(**course_data)
        db.session.add(course)
    
    db.session.commit()
    
    # Create academic records
    academic_records_data = [
        {
            'student_id': 3,  # student1
            'course_id': 1,  # CS101
            'status': 'enrolled',
            'semester': 'Fall',
            'academic_year': '2023-2024'
        },
        {
            'student_id': 3,  # student1
            'course_id': 2,  # CS102
            'status': 'enrolled',
            'semester': 'Fall',
            'academic_year': '2023-2024'
        }
    ]
    
    for record_data in academic_records_data:
        record = AcademicRecord(**record_data)
        db.session.add(record)
    
    db.session.commit()
    
    # Create academic goals
    goals_data = [
        {
            'student_id': 3,  # student1
            'course_id': 1,  # CS101
            'title': 'Improve Programming Skills',
            'description': 'Master basic Python programming concepts',
            'target_grade': 3.5,
            'target_date': datetime.utcnow() + timedelta(days=90)
        }
    ]
    
    for goal_data in goals_data:
        goal = AcademicGoal(**goal_data)
        db.session.add(goal)
    
    db.session.commit()
    
    # Create course materials
    materials_data = [
        {
            'course_id': 1,  # CS101
            'title': 'Python Basics',
            'description': 'Introduction to Python syntax and basic concepts',
            'material_type': 'lecture'
        },
        {
            'course_id': 1,  # CS101
            'title': 'Control Structures',
            'description': 'If statements, loops, and control flow',
            'material_type': 'lecture'
        }
    ]
    
    for material_data in materials_data:
        material = CourseMaterial(**material_data)
        db.session.add(material)
    
    db.session.commit()
    
    # Create assignments
    assignments_data = [
        {
            'course_id': 1,  # CS101
            'title': 'Python Basics Assignment',
            'description': 'Practice basic Python syntax',
            'due_date': datetime.utcnow() + timedelta(days=7),
            'total_points': 100,
            'weight': 20
        }
    ]
    
    for assignment_data in assignments_data:
        assignment = Assignment(**assignment_data)
        db.session.add(assignment)
    
    db.session.commit()
    
    # Create exams
    exams_data = [
        {
            'course_id': 1,  # CS101
            'title': 'Midterm Exam',
            'description': 'Covers Python basics and control structures',
            'exam_date': datetime.utcnow() + timedelta(days=30),
            'duration': 120,  # minutes
            'total_points': 100,
            'weight': 25.0  # 25% of course grade
        }
    ]
    
    for exam_data in exams_data:
        exam = Exam(**exam_data)
        db.session.add(exam)
    
    db.session.commit()
    
    # Create discussions
    discussions_data = [
        {
            'title': 'Python Help',
            'description': 'Get help with Python programming',
            'course_id': 1,  # CS101
            'created_by': 3  # student1
        }
    ]
    
    for discussion_data in discussions_data:
        discussion = Discussion(**discussion_data)
        db.session.add(discussion)
    
    db.session.commit()
    
    # Create discussion posts
    posts_data = [
        {
            'content': 'I need help with Python loops',
            'discussion_id': 1,
            'author_id': 3  # student1
        }
    ]
    
    for post_data in posts_data:
        post = DiscussionPost(**post_data)
        db.session.add(post)
    
    db.session.commit()
    
    # Create announcements
    announcements_data = [
        {
            'title': 'Welcome to CS101',
            'content': 'Welcome to Introduction to Programming!',
            'course_id': 1,  # CS101
            'created_by': 2  # professor1
        }
    ]
    
    for announcement_data in announcements_data:
        announcement = Announcement(**announcement_data)
        db.session.add(announcement)
    
    db.session.commit()
    
    # Create notifications
    notifications_data = [
        {
            'user_id': 3,  # student1
            'title': 'New Assignment',
            'body': 'A new assignment has been posted in CS101',
            'category': 'academic'
        }
    ]
    
    for notification_data in notifications_data:
        notification = Notification(**notification_data)
        db.session.add(notification)
    
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_database() 