from app import create_app, db
from app.models.user import User
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial, Assignment, AssignmentSubmission
from app.models.communication import Message, Notification, Discussion, DiscussionPost
from datetime import datetime, timedelta

def seed_database():
    # Create test users
    users = [
        {
            'username': 'student1',
            'email': 'student1@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'password123',
            'role': 'student'
        },
        {
            'username': 'student2',
            'email': 'student2@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'password': 'password123',
            'role': 'student'
        },
        {
            'username': 'professor1',
            'email': 'professor1@example.com',
            'first_name': 'Robert',
            'last_name': 'Johnson',
            'password': 'password123',
            'role': 'professor'
        }
    ]

    created_users = []
    for user_data in users:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role=user_data['role']
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()

    # Create courses
    courses = [
        {
            'code': 'CS101',
            'name': 'Introduction to Computer Science',
            'description': 'Fundamental concepts of programming and computer science',
            'credits': 3
        },
        {
            'code': 'MATH201',
            'name': 'Calculus I',
            'description': 'Limits, derivatives, and integrals',
            'credits': 4
        },
        {
            'code': 'ENG102',
            'name': 'English Composition',
            'description': 'Academic writing and research skills',
            'credits': 3
        },
        {
            'code': 'PHYS101',
            'name': 'Physics I',
            'description': 'Mechanics and thermodynamics',
            'credits': 4
        }
    ]

    created_courses = []
    for course_data in courses:
        course = Course(**course_data)
        db.session.add(course)
        created_courses.append(course)
    
    db.session.commit()

    # Create academic records
    for student in created_users[:2]:  # First two users are students
        for course in created_courses:
            record = AcademicRecord(
                student_id=student.id,
                course_id=course.id,
                grade=float(format(4.0 * 0.7 + 0.3 * 4.0 * (hash(student.username + course.code) % 100) / 100, '.2f')),
                semester='Fall 2023',
                academic_year='2023-2024',
                status='enrolled'
            )
            db.session.add(record)

    db.session.commit()

    # Create academic goals
    for student in created_users[:2]:
        for course in created_courses[:2]:  # Set goals for first two courses
            goal = AcademicGoal(
                student_id=student.id,
                course_id=course.id,
                target_grade=4.0,
                description=f'Aim to achieve an A in {course.name}',
                deadline=datetime.utcnow() + timedelta(days=90),
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
                material_type=material_type,
                due_date=datetime.utcnow() + timedelta(days=14) if material_type == 'assignment' else None
            )
            db.session.add(material)

    db.session.commit()

    # Create messages between users
    message_contents = [
        'Could you please explain the latest assignment?',
        'When is the next study group meeting?',
        'Thanks for your help with the project!'
    ]

    for content in message_contents:
        message = Message(
            sender_id=created_users[0].id,  # student1
            recipient_id=created_users[1].id,  # student2
            body=content
        )
        db.session.add(message)

    db.session.commit()

    # Create notifications
    notification_types = [
        ('Assignment Due', 'Your assignment for CS101 is due tomorrow', 'academic', 'high'),
        ('New Message', 'You have a new message from a classmate', 'communication', 'normal'),
        ('Grade Posted', 'A new grade has been posted for MATH201', 'academic', 'normal')
    ]

    for student in created_users[:2]:
        for title, body, category, priority in notification_types:
            notification = Notification(
                user_id=student.id,
                title=title,
                body=body,
                category=category,
                priority=priority
            )
            db.session.add(notification)

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
            db.session.commit()

            # Create some submissions for the first student
            if course == created_courses[0]:  # Only for the first course
                submission = AssignmentSubmission(
                    assignment_id=assignment.id,
                    student_id=created_users[0].id,  # student1
                    file_path=f'/submissions/{assignment.id}/submission.pdf',
                    grade=85.0 if 'Midterm' in assignment.title else None,
                    feedback='Good work!' if 'Midterm' in assignment.title else None,
                    status='graded' if 'Midterm' in assignment.title else 'submitted'
                )
                db.session.add(submission)

    db.session.commit()

    # Create discussions
    for course in created_courses:
        discussion = Discussion(
            title=f'General Discussion - {course.name}',
            course_id=course.id,
            created_by=created_users[0].id
        )
        db.session.add(discussion)
        db.session.commit()

        # Add discussion posts
        post = DiscussionPost(
            discussion_id=discussion.id,
            user_id=created_users[0].id,
            content=f'Welcome to the discussion forum for {course.name}!'
        )
        db.session.add(post)

        # Add a reply
        reply = DiscussionPost(
            discussion_id=discussion.id,
            user_id=created_users[1].id,
            content='Thanks for starting this discussion!',
            parent_id=post.id
        )
        db.session.add(reply)

    db.session.commit()

def seed_assignments():
    # Get existing courses and users
    courses = Course.query.all()
    students = User.query.filter_by(role='student').all()

    if not courses or not students:
        print("No courses or students found. Please run the full seed_database() first.")
        return

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

    for course in courses:
        for assignment_data in assignments:
            # Check if assignment already exists
            existing = Assignment.query.filter_by(
                course_id=course.id,
                title=assignment_data['title']
            ).first()
            
            if not existing:
                assignment = Assignment(
                    course_id=course.id,
                    **assignment_data
                )
                db.session.add(assignment)
                db.session.commit()

                # Create some submissions for the first student
                if course == courses[0] and students:  # Only for the first course
                    submission = AssignmentSubmission(
                        assignment_id=assignment.id,
                        student_id=students[0].id,
                        file_path=f'/submissions/{assignment.id}/submission.pdf',
                        grade=85.0 if 'Midterm' in assignment.title else None,
                        feedback='Good work!' if 'Midterm' in assignment.title else None,
                        status='graded' if 'Midterm' in assignment.title else 'submitted'
                    )
                    db.session.add(submission)
                    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Seed only assignments
        seed_assignments()
        print("Assignments seeded successfully!") 