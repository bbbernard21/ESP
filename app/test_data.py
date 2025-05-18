from app import db
from app.models.academic import (
    Course, AcademicRecord, Assignment, AssignmentSubmission,
    Quiz, QuizSubmission, Exam, ExamGrade,
    SemesterGoal, ModuleGoal, CourseMaterial
)
from datetime import datetime, timedelta
from sqlalchemy import or_

def create_test_data(user_id):
    """Create test data for goal settings feature."""
    
    # Delete existing test data for this user
    ModuleGoal.query.filter(
        ModuleGoal.semester_goal_id.in_(
            SemesterGoal.query.filter_by(student_id=user_id).with_entities(SemesterGoal.id)
        )
    ).delete(synchronize_session=False)
    
    SemesterGoal.query.filter_by(student_id=user_id).delete()
    
    AssignmentSubmission.query.filter_by(student_id=user_id).delete()
    QuizSubmission.query.filter_by(student_id=user_id).delete()
    ExamGrade.query.filter_by(student_id=user_id).delete()
    
    Assignment.query.filter(
        Assignment.course_id.in_(
            Course.query.filter(
                Course.code.in_(['CS101', 'CS201', 'CS301', 'CS401'])
            ).with_entities(Course.id)
        )
    ).delete(synchronize_session=False)
    
    Quiz.query.filter(
        Quiz.course_id.in_(
            Course.query.filter(
                Course.code.in_(['CS101', 'CS201', 'CS301', 'CS401'])
            ).with_entities(Course.id)
        )
    ).delete(synchronize_session=False)
    
    Exam.query.filter(
        Exam.course_id.in_(
            Course.query.filter(
                Course.code.in_(['CS101', 'CS201', 'CS301', 'CS401'])
            ).with_entities(Course.id)
        )
    ).delete(synchronize_session=False)
    
    AcademicRecord.query.filter_by(student_id=user_id).delete()
    
    Course.query.filter(
        Course.code.in_(['CS101', 'CS201', 'CS301', 'CS401'])
    ).delete()
    
    db.session.commit()
    
    # Create test courses
    courses = [
        Course(
            name='Introduction to Computer Science',
            code='CS101',
            credits=3,
            description='Fundamental concepts of programming',
            semester='Fall',
            status='active'
        ),
        Course(
            name='Data Structures',
            code='CS201',
            credits=4,
            description='Advanced data structures and algorithms',
            semester='Fall',
            status='active'
        ),
        Course(
            name='Database Systems',
            code='CS301',
            credits=3,
            description='Database design and SQL',
            semester='Fall',
            status='active'
        ),
        Course(
            name='Software Engineering',
            code='CS401',
            credits=4,
            description='Software development lifecycle',
            semester='Fall',
            status='active'
        )
    ]
    
    for course in courses:
        db.session.add(course)
    db.session.commit()
    
    # Create enrollments
    for course in courses:
        academic_record = AcademicRecord(
            student_id=user_id,
            course_id=course.id,
            status='enrolled',
            semester='Fall',
            academic_year='2023-2024'
        )
        db.session.add(academic_record)
    db.session.commit()
    
    now = datetime.utcnow()
    
    # Create assessments for each course
    for course in courses:
        # Regular assignments
        assignments = [
            Assignment(
                course_id=course.id,
                title=f'Assignment 1 - {course.code}',
                description='First assignment',
                due_date=now - timedelta(days=30),
                total_points=100,
                weight=10
            ),
            Assignment(
                course_id=course.id,
                title=f'Assignment 2 - {course.code}',
                description='Second assignment',
                due_date=now + timedelta(days=45),
                total_points=100,
                weight=10
            )
        ]
        
        # Quizzes
        quizzes = [
            Quiz(
                course_id=course.id,
                title=f'Quiz 1 - {course.code}',
                description='First quiz',
                total_marks=100,
                duration=60,
                start_time=now - timedelta(days=20),
                end_time=now - timedelta(days=19),
                weight=15
            ),
            Quiz(
                course_id=course.id,
                title=f'Quiz 2 - {course.code}',
                description='Second quiz',
                total_marks=100,
                duration=60,
                start_time=now + timedelta(days=10),
                end_time=now + timedelta(days=11),
                weight=15
            )
        ]
        
        # Exams
        exams = [
            Exam(
                course_id=course.id,
                title=f'Midterm - {course.code}',
                description='Midterm exam',
                exam_date=now + timedelta(days=15),
                duration=120,
                total_points=100,
                weight=25
            ),
            Exam(
                course_id=course.id,
                title=f'Final - {course.code}',
                description='Final exam',
                exam_date=now + timedelta(days=60),
                duration=180,
                total_points=100,
                weight=25
            )
        ]
        
        # Add all assessments to database
        for assignment in assignments:
            db.session.add(assignment)
        for quiz in quizzes:
            db.session.add(quiz)
        for exam in exams:
            db.session.add(exam)
    db.session.commit()
    
    # Add completed assignment submissions
    assignments = Assignment.query.filter(Assignment.due_date < now).all()
    for assignment in assignments:
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_id=user_id,
            grade=85.0 if 'CS101' in assignment.title else (
                78.0 if 'CS201' in assignment.title else (
                    92.0 if 'CS301' in assignment.title else 88.0
                )
            ),
            status='graded',
            submitted_at=assignment.due_date - timedelta(days=1),
            graded_at=assignment.due_date + timedelta(days=1)
        )
        db.session.add(submission)
    
    # Add completed quiz submissions
    quizzes = Quiz.query.filter(Quiz.end_time < now).all()
    for quiz in quizzes:
        submission = QuizSubmission(
            quiz_id=quiz.id,
            student_id=user_id,
            score=85.0 if 'CS101' in quiz.title else (
                78.0 if 'CS201' in quiz.title else (
                    92.0 if 'CS301' in quiz.title else 88.0
                )
            ),
            status='completed',
            submitted_at=quiz.end_time - timedelta(hours=1)
        )
        db.session.add(submission)
    
    # Add completed exam grades
    exams = Exam.query.filter(Exam.exam_date < now).all()
    for exam in exams:
        grade = ExamGrade(
            exam_id=exam.id,
            student_id=user_id,
            grade=85.0 if 'CS101' in exam.title else (
                78.0 if 'CS201' in exam.title else (
                    92.0 if 'CS301' in exam.title else 88.0
                )
            ),
            graded_at=exam.exam_date + timedelta(days=1)
        )
        db.session.add(grade)
    
    db.session.commit()
    
    # Create a semester goal
    semester_goal = SemesterGoal(
        student_id=user_id,
        academic_year='2023-2024',
        semester='Fall',
        target_gpa=3.5,
        current_gpa=3.2
    )
    db.session.add(semester_goal)
    db.session.commit()
    
    # Create module goals
    module_goals = [
        ModuleGoal(
            semester_goal_id=semester_goal.id,
            course_id=courses[0].id,  # CS101
            target_grade=85.0,
            current_grade=85.0
        ),
        ModuleGoal(
            semester_goal_id=semester_goal.id,
            course_id=courses[1].id,  # CS201
            target_grade=80.0,
            current_grade=78.0
        ),
        ModuleGoal(
            semester_goal_id=semester_goal.id,
            course_id=courses[2].id,  # CS301
            target_grade=90.0,
            current_grade=92.0
        ),
        ModuleGoal(
            semester_goal_id=semester_goal.id,
            course_id=courses[3].id,  # CS401
            target_grade=85.0,
            current_grade=88.0
        )
    ]
    
    for goal in module_goals:
        db.session.add(goal)
    db.session.commit()
    
    return {
        'courses': courses,
        'semester_goal': semester_goal,
        'module_goals': module_goals
    } 

def add_learning_material_to_all_courses():
    """Add the learning material to all active courses."""
    courses = Course.query.filter_by(status='active').all()
    
    for course in courses:
        # Check if material already exists
        existing_material = CourseMaterial.query.filter_by(
            course_id=course.id,
            title="Learning Material"
        ).first()
        
        if not existing_material:
            material = CourseMaterial(
                course_id=course.id,
                title="Learning Material",
                description="PowerPoint presentation for learning materials",
                file_path="course_materials/learning_material.pptx",
                material_type="presentation",
                created_at=datetime.utcnow()
            )
            
            try:
                db.session.add(material)
                db.session.commit()
                print(f"Added learning material to course: {course.name}")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding material to course {course.name}: {str(e)}")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        add_learning_material_to_all_courses() 