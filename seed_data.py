from app import create_app, db
from app.models.user import User
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial, Program, Assignment, AssignmentSubmission, Exam, ExamGrade
from app.models.communication import Message, Notification, Discussion, DiscussionPost
from datetime import datetime, timedelta
from app.models.user import UserRole

def seed_database():
    # Create programs first
    programs = [
        {
            'code': 'CS',
            'name': 'Computer Science',
            'description': 'Study of computation, automation, and information.'
        },
        {
            'code': 'MATH',
            'name': 'Mathematics',
            'description': 'Study of numbers, quantities, and shapes.'
        },
        {
            'code': 'ENG',
            'name': 'English',
            'description': 'Study of literature, writing, and communication.'
        },
        {
            'code': 'PHYS',
            'name': 'Physics',
            'description': 'Study of matter, energy, and their interactions.'
        }
    ]

    created_programs = []
    for program_data in programs:
        program = Program(**program_data)
        db.session.add(program)
        created_programs.append(program)
    
    db.session.commit()

    # Create test users with program assignments for students
    users = [
        {
            'username': 'student1',
            'email': 'student1@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'password123',
            'role': UserRole.STUDENT.value,
            'is_active': True,
            'last_login': datetime.utcnow(),
            'program_id': created_programs[0].id  # CS program
        },
        {
            'username': 'student2',
            'email': 'student2@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'password': 'password123',
            'role': UserRole.STUDENT.value,
            'is_active': True,
            'last_login': datetime.utcnow(),
            'program_id': created_programs[1].id  # MATH program
        },
        {
            'username': 'professor1',
            'email': 'professor1@example.com',
            'first_name': 'Robert',
            'last_name': 'Johnson',
            'password': 'password123',
            'role': UserRole.PROFESSOR.value,
            'is_active': True,
            'last_login': datetime.utcnow()
        },
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'password': 'admin123',
            'role': UserRole.ADMIN.value,
            'is_active': True,
            'last_login': datetime.utcnow()
        }
    ]

    created_users = []
    for user_data in users:
        password = user_data.pop('password')
        user = User(**user_data)
        user.set_password(password)
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()

    # Create courses with program assignments
    courses = [
        {
            'code': 'CS101',
            'name': 'Introduction to Programming',
            'description': 'Basic programming concepts using Python',
            'credits': 3,
            'program': created_programs[0],  # CS program
            'professor': created_users[2],  # professor1
            'assignments_weight': 40.0,
            'midterm_weight': 25.0,
            'final_weight': 35.0,
            'semester': 'Fall',
            'status': 'active'
        },
        {
            'code': 'CS102',
            'name': 'Data Structures',
            'description': 'Fundamental data structures and algorithms',
            'credits': 3,
            'program': created_programs[0],  # CS program
            'professor': created_users[2],  # professor1
            'assignments_weight': 40.0,
            'midterm_weight': 25.0,
            'final_weight': 35.0,
            'semester': 'Fall',
            'status': 'active'
        },
        {
            'code': 'MATH101',
            'name': 'Calculus I',
            'description': 'Limits, derivatives, and integrals',
            'credits': 4,
            'program': created_programs[1],  # MATH program
            'professor': created_users[2],  # professor1
            'assignments_weight': 40.0,
            'midterm_weight': 25.0,
            'final_weight': 35.0,
            'semester': 'Fall',
            'status': 'active'
        },
        {
            'code': 'PHYS101',
            'name': 'Physics I',
            'description': 'Mechanics and thermodynamics',
            'credits': 4,
            'program': created_programs[3],  # PHYS program
            'professor': created_users[2],  # professor1
            'assignments_weight': 40.0,
            'midterm_weight': 25.0,
            'final_weight': 35.0,
            'semester': 'Fall',
            'status': 'active'
        }
    ]

    created_courses = []
    for course_data in courses:
        program = course_data.pop('program')
        professor = course_data.pop('professor')
        course = Course(**course_data)
        course.program = program
        course.professor = professor
        db.session.add(course)
        created_courses.append(course)
    
    db.session.commit()

    # Create academic records based on program enrollment
    current_year = datetime.utcnow().year
    academic_year = f"{current_year}-{current_year+1}"
    current_month = datetime.utcnow().month
    semester = 'Fall' if 8 <= current_month <= 12 else 'Spring' if 1 <= current_month <= 5 else 'Summer'

    for student in created_users[:2]:  # First two users are students
        # Get courses for student's program
        program_courses = [c for c in created_courses if c.program_id == student.program_id]
        for course in program_courses:
            record = AcademicRecord(
                student_id=student.id,
                course_id=course.id,
                grade=None,  # Initialize with no grade
                status='enrolled',
                enrollment_date=datetime.utcnow(),
                semester=semester,
                academic_year=academic_year
            )
            db.session.add(record)

    db.session.commit()

    # Create academic goals for enrolled courses
    for student in created_users[:2]:
        program_courses = [c for c in created_courses if c.program_id == student.program_id]
        for course in program_courses:
            goal = AcademicGoal(
                student_id=student.id,
                course_id=course.id,
                title=f'Get an A in {course.name}',
                description=f'Aim to achieve an A in {course.name}',
                target_date=datetime.utcnow() + timedelta(days=90),
                status='active'
            )
            db.session.add(goal)

    db.session.commit()

    # Create course materials
    material_types = ['lecture', 'assignment', 'reading']
    for course in created_courses:
        for i, material_type in enumerate(material_types):
            material = CourseMaterial(
                course_id=course.id,
                title=f'{material_type.title()} {i+1} - {course.name}',
                description=f'Material for {course.name}',
                file_path=f'/materials/{course.code}/{material_type}_{i+1}.pdf',
                material_type=material_type
            )
            db.session.add(material)

    db.session.commit()

    # Create assignments
    assignments = [
        {
            'title': 'Midterm Project',
            'description': 'Individual project implementing core concepts',
            'total_points': 100,
            'weight': 30,  # 30% of course grade
            'due_date': datetime.utcnow() + timedelta(days=30)
        },
        {
            'title': 'Final Assignment',
            'description': 'Comprehensive assignment covering all topics',
            'total_points': 100,
            'weight': 40,  # 40% of course grade
            'due_date': datetime.utcnow() + timedelta(days=60)
        }
    ]

    for course in created_courses:
        for assignment_data in assignments:
            assignment = Assignment(
                course_id=course.id,
                **assignment_data
            )
            db.session.add(assignment)
            db.session.commit()  # Commit the assignment first
            
            # Create submissions only for enrolled students
            enrolled_students = [
                record.student for record in course.academic_records
                if record.status == 'enrolled'
            ]
            
            for student in enrolled_students:
                submission = AssignmentSubmission(
                    assignment_id=assignment.id,
                    student_id=student.id,
                    grade=85.0,
                    feedback='Good work, but could improve documentation',
                    status='graded',
                    submitted_at=datetime.utcnow() - timedelta(days=2),
                    graded_at=datetime.utcnow() - timedelta(days=1)
                )
                db.session.add(submission)

    db.session.commit()

    # Create exams for each course
    exam_types = ['Midterm', 'Final']
    for course in created_courses:
        for exam_type in exam_types:
            exam = Exam(
                course_id=course.id,
                title=f'{exam_type} Exam - {course.name}',
                description=f'{exam_type} examination for {course.name}',
                total_points=100,
                exam_date=datetime.utcnow() + timedelta(days=45 if exam_type == 'Midterm' else 90),
                duration=180,  # 3 hours in minutes
                weight=25.0 if exam_type == 'Midterm' else 35.0
            )
            db.session.add(exam)
            db.session.commit()  # Commit to get exam.id
            
            # Create exam grades for enrolled students
            enrolled_students = [
                record.student for record in course.academic_records
                if record.status == 'enrolled'
            ]
            
            for student in enrolled_students:
                exam_grade = ExamGrade(
                    exam_id=exam.id,
                    student_id=student.id,
                    grade=88.0,
                    feedback='Good understanding of concepts',
                    graded_at=datetime.utcnow()
                )
                db.session.add(exam_grade)

    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_database() 