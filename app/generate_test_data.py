import os
import random
from datetime import datetime, timedelta
from app import create_app, db
from app.models.user import User, UserRole
from app.models.academic import Program, Course, AcademicRecord, AcademicGoal, CourseMaterial, Assignment, AssignmentSubmission, Exam, ExamGrade, Quiz, QuizSubmission, SemesterGoal, ModuleGoal
from app.models.communication import Announcement, Message, GroupChat, ChatParticipant, ChatMessage, Discussion, DiscussionPost, Notification
from app.models.faq import FAQ

# --- CONFIGURABLE ---
NEW_USERS = [
    {'username': 'alice.smith', 'email': 'alice.smith@test.edu', 'role': UserRole.STUDENT, 'first_name': 'Alice', 'last_name': 'Smith'},
    {'username': 'bob.jones', 'email': 'bob.jones@test.edu', 'role': UserRole.STUDENT, 'first_name': 'Bob', 'last_name': 'Jones'},
    {'username': 'carol.lee', 'email': 'carol.lee@test.edu', 'role': UserRole.STUDENT, 'first_name': 'Carol', 'last_name': 'Lee'},
    {'username': 'prof.johnson', 'email': 'prof.johnson@test.edu', 'role': UserRole.PROFESSOR, 'first_name': 'Emily', 'last_name': 'Johnson'},
    {'username': 'prof.miller', 'email': 'prof.miller@test.edu', 'role': UserRole.PROFESSOR, 'first_name': 'David', 'last_name': 'Miller'},
    {'username': 'admin', 'email': 'admin@test.edu', 'role': UserRole.ADMIN, 'first_name': 'Admin', 'last_name': 'User'},
]

NEW_PROGRAMS = [
    {'name': 'Computer Science', 'code': 'CS', 'description': 'BSc in Computer Science', 'duration': 8},
    {'name': 'Business Administration', 'code': 'BUS', 'description': 'BBA in Business Administration', 'duration': 8},
]

NEW_COURSES = [
    {'name': 'Intro to Programming', 'code': 'CS101', 'program_code': 'CS', 'professor_username': 'prof.johnson', 'semester': 'Fall', 'description': 'Learn programming basics.'},
    {'name': 'Data Structures', 'code': 'CS102', 'program_code': 'CS', 'professor_username': 'prof.johnson', 'semester': 'Spring', 'description': 'Learn about data structures.'},
    {'name': 'Principles of Management', 'code': 'BUS101', 'program_code': 'BUS', 'professor_username': 'prof.miller', 'semester': 'Fall', 'description': 'Introduction to management.'},
]

ASSIGNMENTS = [
    {'title': 'Assignment 1', 'description': 'First assignment', 'due_delta': 7},
    {'title': 'Assignment 2', 'description': 'Second assignment', 'due_delta': 14},
]
QUIZZES = [
    {'title': 'Quiz 1', 'description': 'First quiz', 'due_delta': 10},
]
EXAMS = [
    {'title': 'Midterm', 'description': 'Midterm exam', 'due_delta': 20},
    {'title': 'Final', 'description': 'Final exam', 'due_delta': 35},
]
MATERIALS = [
    {'title': 'Syllabus', 'description': 'Course syllabus', 'material_type': 'document'},
    {'title': 'Lecture 1 Slides', 'description': 'Slides for lecture 1', 'material_type': 'slides'},
]
ANNOUNCEMENTS = [
    {'title': 'Welcome!', 'content': 'Welcome to the course!'},
    {'title': 'Exam Info', 'content': 'Midterm will be next week.'},
]
FAQS = [
    {'question': 'How do I reset my password?', 'answer': "Use the 'Forgot Password' link on the login page."},
    {'question': 'How to submit assignments?', 'answer': 'Go to the course page and click Submit Assignment.'},
]

def main():
    app, _ = create_app()
    with app.app_context():
        # --- USERS ---
        users = {}
        for u in NEW_USERS:
            user = User.query.filter_by(username=u['username']).first()
            if not user:
                user = User(username=u['username'], email=u['email'], role=u['role'].value, first_name=u['first_name'], last_name=u['last_name'])
                user.set_password('password123')
                db.session.add(user)
            users[u['username']] = user
        db.session.commit()

        # --- PROGRAMS ---
        programs = {}
        for p in NEW_PROGRAMS:
            prog = Program.query.filter_by(code=p['code']).first()
            if not prog:
                prog = Program(name=p['name'], code=p['code'], description=p['description'], duration=p['duration'])
                db.session.add(prog)
            programs[p['code']] = prog
        db.session.commit()

        # --- PROFESSORS (ensure all exist before creating courses) ---
        professor_usernames = set(c['professor_username'] for c in NEW_COURSES)
        for prof_username in professor_usernames:
            if prof_username not in users:
                print(f"INFO: Creating missing professor '{prof_username}' for test data.")
                prof = User(username=prof_username, email=f"{prof_username}@test.edu", role=UserRole.PROFESSOR.value, first_name=prof_username.split('.')[0].capitalize(), last_name=prof_username.split('.')[-1].capitalize())
                prof.set_password('password123')
                db.session.add(prof)
                db.session.commit()
                users[prof_username] = prof
        # --- COURSES ---
        for c in NEW_COURSES:
            professor = users[c['professor_username']]
            if not professor or professor.role != UserRole.PROFESSOR.value:
                raise Exception(f"Course '{c['code']}' references invalid or missing professor '{c['professor_username']}'. Test data generation aborted.")
            course = Course.query.filter_by(code=c['code']).first()
            if not course:
                course = Course(name=c['name'], code=c['code'], description=c['description'], program=programs[c['program_code']], professor=professor, semester=c['semester'], credits=3)
                db.session.add(course)
        db.session.commit()  # Ensure Course objects have IDs assigned
        # Re-query courses to ensure IDs are set
        courses = {c['code']: Course.query.filter_by(code=c['code']).first() for c in NEW_COURSES}
        print('DEBUG: Courses after commit:')
        for code, course in courses.items():
            print(f'  {code}: {course} (id={getattr(course, "id", None)}, professor={getattr(course.professor, "username", None)})')
        # Confirm all courses have valid professors
        missing_prof = [code for code, course in courses.items() if not course.professor]
        if missing_prof:
            print(f"ERROR: The following courses have no professor assigned: {missing_prof}")
        else:
            print("All courses have valid professors assigned.")

        # --- ENROLL STUDENTS ---
        student_usernames = [u['username'] for u in NEW_USERS if u['role'] == UserRole.STUDENT]
        for s in student_usernames:
            for c in courses.values():
                record = AcademicRecord.query.filter_by(student_id=users[s].id, course_id=c.id).first()
                if not record:
                    record = AcademicRecord(student_id=users[s].id, course_id=c.id, status='enrolled', semester=c.semester, academic_year='2024-2025')
                    db.session.add(record)
        db.session.commit()

        # --- ASSIGNMENTS, QUIZZES, EXAMS, MATERIALS ---
        now = datetime.utcnow()
        for c in courses.values():
            # Assignments
            for a in ASSIGNMENTS:
                due = now + timedelta(days=a['due_delta'])
                assignment = Assignment.query.filter_by(title=a['title'], course_id=c.id).first()
                if not assignment:
                    assignment = Assignment(title=a['title'], description=a['description'], due_date=due, course_id=c.id)
                    db.session.add(assignment)
            # Quizzes
            for q in QUIZZES:
                quiz_due = now + timedelta(days=q['due_delta'])
                quiz = Quiz.query.filter_by(title=q['title'], course_id=c.id).first()
                if not quiz:
                    quiz = Quiz(title=q['title'], description=q['description'], start_time=quiz_due - timedelta(hours=1), end_time=quiz_due, course_id=c.id)
                    db.session.add(quiz)
            # Exams
            for e in EXAMS:
                exam_due = now + timedelta(days=e['due_delta'])
                print(f"DEBUG: Creating Exam for course {c} with id {getattr(c, 'id', None)}")
                if c.id is not None:
                    exam = Exam.query.filter_by(title=e['title'], course_id=c.id).first()
                    if not exam:
                        exam = Exam(
                            title=e['title'],
                            description=e['description'],
                            course_id=c.id,
                            exam_date=exam_due,
                            duration=120,
                            total_points=100.0,
                            weight=1.0
                        )
                        db.session.add(exam)
                else:
                    print(f"ERROR: Course {c} has no id! Skipping exam creation.")
            # Materials
            for m in MATERIALS:
                mat = CourseMaterial.query.filter_by(title=m['title'], course_id=c.id).first()
                if not mat:
                    mat = CourseMaterial(title=m['title'], description=m['description'], material_type=m['material_type'], course_id=c.id)
                    db.session.add(mat)
        db.session.commit()

        # --- ANNOUNCEMENTS ---
        for c in courses.values():
            for a in ANNOUNCEMENTS:
                ann = Announcement.query.filter_by(title=a['title'], course_id=c.id).first()
                if not ann:
                    if c.professor is not None:
                        ann = Announcement(title=a['title'], content=a['content'], course_id=c.id, created_by=c.professor.id)
                        db.session.add(ann)
                    else:
                        print(f"WARNING: Course {c.code} has no professor assigned. Skipping announcement creation.")
        db.session.commit()

        # --- FAQ ---
        for f in FAQS:
            faq = FAQ.query.filter_by(question=f['question']).first()
            if not faq:
                faq = FAQ(question=f['question'], answer=f['answer'])
                db.session.add(faq)
        db.session.commit()

        # --- SUBMISSIONS, GRADES, GOALS ---
        for s in student_usernames:
            student = users[s]
            for c in courses.values():
                # Assignments
                for a in ASSIGNMENTS:
                    assignment = Assignment.query.filter_by(title=a['title'], course_id=c.id).first()
                    if assignment:
                        # Randomly choose if student submitted
                        submitted = random.choice([True, False])
                        if submitted:
                            sub = AssignmentSubmission.query.filter_by(assignment_id=assignment.id, student_id=student.id).first()
                            if not sub:
                                sub = AssignmentSubmission(assignment_id=assignment.id, student_id=student.id, submitted_at=now + timedelta(days=random.randint(-2, 2)), status='submitted', grade=random.randint(60, 100))
                                db.session.add(sub)
                # Quizzes
                for q in QUIZZES:
                    quiz = Quiz.query.filter_by(title=q['title'], course_id=c.id).first()
                    if quiz:
                        submitted = random.choice([True, False])
                        if submitted:
                            sub = QuizSubmission.query.filter_by(quiz_id=quiz.id, student_id=student.id).first()
                            if not sub:
                                sub = QuizSubmission(quiz_id=quiz.id, student_id=student.id, submitted_at=now + timedelta(days=random.randint(-2, 2)), score=random.randint(60, 100))
                                db.session.add(sub)
                # Exams
                for e in EXAMS:
                    exam = Exam.query.filter_by(title=e['title'], course_id=c.id).first()
                    if exam:
                        graded = random.choice([True, False])
                        if graded:
                            eg = ExamGrade.query.filter_by(exam_id=exam.id, student_id=student.id).first()
                            if not eg:
                                eg = ExamGrade(exam_id=exam.id, student_id=student.id, grade=random.randint(50, 100))
                                db.session.add(eg)
                # Academic Goals
                goal = AcademicGoal.query.filter_by(student_id=student.id, course_id=c.id).first()
                if not goal:
                    goal = AcademicGoal(student_id=student.id, course_id=c.id, title=f"Goal for {c.code}", description="Achieve at least 75%", target_grade=75.0)
                    db.session.add(goal)
            # Semester Goal
            sem_goal = SemesterGoal.query.filter_by(student_id=student.id, academic_year='2024-2025', semester='Fall').first()
            if not sem_goal:
                sem_goal = SemesterGoal(student_id=student.id, academic_year='2024-2025', semester='Fall', target_gpa=3.5)
                db.session.add(sem_goal)
            # Module Goals
            for c in courses.values():
                mod_goal = ModuleGoal.query.filter_by(semester_goal_id=sem_goal.id, course_id=c.id).first()
                if not mod_goal:
                    mod_goal = ModuleGoal(semester_goal_id=sem_goal.id, course_id=c.id, target_grade=80.0)
                    db.session.add(mod_goal)
        db.session.commit()

        # --- MESSAGES, GROUP CHATS, DISCUSSIONS ---
        # Direct message student to professor
        for s in student_usernames:
            student = users[s]
            for c in courses.values():
                prof = c.professor
                if prof is None:
                    print(f"ERROR: Course {c.code} has no professor assigned when creating message. Skipping.")
                    continue
                msg = Message(sender_id=student.id, recipient_id=prof.id, conversation_id=1, body=f"Hi {prof.first_name}, I have a question about {c.code}.")
                db.session.add(msg)
        db.session.commit()
        # Group chat for each course
        for c in courses.values():
            if c.professor is None:
                print(f"ERROR: Course {c.code} has no professor assigned when creating group chat. Skipping group chat creation.")
                continue
            chat = GroupChat.query.filter_by(name=f"{c.code} Group").first()
            if not chat:
                chat = GroupChat(name=f"{c.code} Group", is_group=True, created_by_id=c.professor.id)
                db.session.add(chat)
                db.session.commit()
            for s in student_usernames:
                student = users[s]
                if not ChatParticipant.query.filter_by(chat_id=chat.id, user_id=student.id).first():
                    db.session.add(ChatParticipant(chat_id=chat.id, user_id=student.id))
            db.session.commit()
            # Add a chat message
            msg = ChatMessage(chat_id=chat.id, sender_id=c.professor.id, body=f"Welcome to {c.code} group chat!")
            db.session.add(msg)
        db.session.commit()
        # Discussion
        for c in courses.values():
            disc = Discussion.query.filter_by(title=f"{c.code} Discussion").first()
            if not disc:
                disc = Discussion(title=f"{c.code} Discussion", description="General Q&A", course_id=c.id, created_by=c.professor.id)
                db.session.add(disc)
                db.session.commit()
            for s in student_usernames:
                student = users[s]
                post = DiscussionPost.query.filter_by(discussion_id=disc.id, author_id=student.id).first()
                if not post:
                    post = DiscussionPost(discussion_id=disc.id, author_id=student.id, content=f"I have a question about {c.code}.")
                    db.session.add(post)
            db.session.commit()

        print('Test data generated!')

if __name__ == '__main__':
    main()
