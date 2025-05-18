from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, abort
from flask_login import login_required, current_user
import os
from app.models.user import User, UserRole
from app.models.academic import (
    Course, AcademicRecord, Assignment, AssignmentSubmission, 
    Quiz, QuizSubmission, Exam, ExamGrade, CourseMaterial, AcademicGoal, SemesterGoal, ModuleGoal
)
from app.models.communication import Message, Notification, Conversation, Announcement, Discussion, DiscussionPost, Attachment
from app.decorators import student_required
from app import db
from datetime import datetime, timedelta

student = Blueprint('student', __name__)

@student.route('/student/dashboard')
@login_required
@student_required
def dashboard():
    # Get enrolled courses
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    # Calculate overall GPA
    academic_records = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        status='enrolled'
    ).all()
    grades = [r.grade for r in academic_records if r.grade is not None]
    overall_gpa = sum(grades) / len(grades) if grades else 0.0
    
    # Get pending tasks (assignments and exams)
    pending_assignments = Assignment.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        Assignment.due_date > datetime.utcnow(),
        ~AssignmentSubmission.query.filter(
            AssignmentSubmission.student_id == current_user.id,
            AssignmentSubmission.assignment_id == Assignment.id
        ).exists()
    ).all()
    
    pending_exams = Exam.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        Exam.exam_date > datetime.utcnow(),
        ~ExamGrade.query.filter(
            ExamGrade.student_id == current_user.id,
            ExamGrade.exam_id == Exam.id
        ).exists()
    ).all()
    
    pending_tasks = []
    for assignment in pending_assignments:
        pending_tasks.append({
            'type': 'Assignment',
            'course': assignment.course,
            'title': assignment.title,
            'due_date': assignment.due_date,
            'action_url': url_for('student.view_assignment', assignment_id=assignment.id),
            'action_text': 'View'
        })
    
    for exam in pending_exams:
        pending_tasks.append({
            'type': 'Exam',
            'course': exam.course,
            'title': exam.title,
            'due_date': exam.exam_date,
            'action_url': url_for('student.view_exam', exam_id=exam.id),
            'action_text': 'View'
        })
    
    # Sort tasks by due date
    pending_tasks.sort(key=lambda x: x['due_date'])
    
    # Get course progress data
    for course in enrolled_courses:
        try:
            # Calculate progress
            total_assignments = Assignment.query.filter_by(course_id=course.id).count()
            completed_assignments = AssignmentSubmission.query.join(Assignment).filter(
                Assignment.course_id == course.id,
                AssignmentSubmission.student_id == current_user.id,
                AssignmentSubmission.status == 'graded'
            ).count()
            
            course.progress = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
            
            # Get current grade
            submissions = AssignmentSubmission.query.join(Assignment).filter(
                Assignment.course_id == course.id,
                AssignmentSubmission.student_id == current_user.id,
                AssignmentSubmission.status == 'graded'
            ).all()
            
            grades = [s.grade for s in submissions if s.grade is not None]
            course.current_grade = f"{sum(grades) / len(grades):.1f}%" if grades else "N/A"
            
            # Get next task
            next_assignment = Assignment.query.filter(
                Assignment.course_id == course.id,
                Assignment.due_date > datetime.utcnow()
            ).order_by(Assignment.due_date).first()
            
            course.next_task = next_assignment.title if next_assignment else "No upcoming tasks"
        except Exception as e:
            # Set default values if any calculation fails
            course.progress = 0
            course.current_grade = "N/A"
            course.next_task = "No upcoming tasks"
    
    # Get recent activities
    recent_submissions = AssignmentSubmission.query.filter_by(
        student_id=current_user.id
    ).order_by(AssignmentSubmission.submitted_at.desc()).limit(5).all()
    
    recent_grades = AssignmentSubmission.query.filter_by(
        student_id=current_user.id,
        status='graded'
    ).order_by(AssignmentSubmission.graded_at.desc()).limit(5).all()
    
    recent_activities = []
    for submission in recent_submissions:
        try:
            recent_activities.append({
                'title': f"Submitted: {submission.assignment.title}",
                'description': "Assignment submitted successfully",
                'timestamp': submission.submitted_at,
                'course': submission.assignment.course
            })
        except Exception as e:
            continue
    
    for grade in recent_grades:
        try:
            recent_activities.append({
                'title': f"Graded: {grade.assignment.title}",
                'description': f"Grade received: {grade.grade}/{grade.assignment.total_points}",
                'timestamp': grade.graded_at,
                'course': grade.assignment.course
            })
        except Exception as e:
            continue
    
    # Sort activities by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]  # Keep only 5 most recent
    
    # Placeholder for achievements (to be implemented)
    achievements = []
    
    return render_template('student/dashboard.html',
                         title='Student Dashboard',
                         overall_gpa=overall_gpa,
                         enrolled_courses=enrolled_courses,
                         pending_tasks=pending_tasks,
                         achievements=achievements,
                         recent_activities=recent_activities,
                         now=datetime.utcnow())

@student.route('/student/course/<int:course_id>')
@login_required
@student_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get assignments
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    # Get other assessments separately
    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    exams = Exam.query.filter_by(course_id=course_id).all()
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    return render_template('student/course_detail.html',
                         course=course,
                         assignments=assignments,
                         quizzes=quizzes,
                         exams=exams,
                         materials=materials,
                         now=datetime.utcnow())

@student.route('/student/course/<int:course_id>/materials')
@login_required
@student_required
def course_materials(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment
    AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    return render_template('student/course_materials.html',
                         title=f'{course.name} - Materials',
                         course=course,
                         materials=materials)

@student.route('/student/goals')
@login_required
@student_required
def goals():
    academic_goals = AcademicGoal.query.filter_by(
        student_id=current_user.id
    ).order_by(AcademicGoal.target_date).all()
    
    return render_template('student/goals.html',
                         title='Academic Goals',
                         goals=academic_goals)

@student.route('/student/goal/create', methods=['GET', 'POST'])
@login_required
@student_required
def create_goal():
    if request.method == 'POST':
        try:
            goal = AcademicGoal(
                student_id=current_user.id,
                course_id=request.form['course_id'],
                target_grade=float(request.form['target_grade']),
                description=request.form['description'],
                deadline=datetime.strptime(request.form['deadline'], '%Y-%m-%d'),
                status='active'
            )
            db.session.add(goal)
            db.session.commit()
            flash('Goal created successfully!', 'success')
            return redirect(url_for('student.goals'))
        except Exception as e:
            flash(f'Error creating goal: {str(e)}', 'error')
    
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    return render_template('student/create_goal.html',
                         title='Create Goal',
                         courses=enrolled_courses)

@student.route('/student/goal/<int:goal_id>/update', methods=['POST'])
@login_required
@student_required
def update_goal(goal_id):
    goal = AcademicGoal.query.get_or_404(goal_id)
    if goal.student_id != current_user.id:
        flash('You do not have permission to update this goal.', 'error')
        return redirect(url_for('student.goals'))
    try:
        goal.title = request.form['title']
        goal.description = request.form['description']
        goal.target_date = datetime.strptime(request.form['target_date'], '%Y-%m-%d')
        goal.status = request.form.get('status', goal.status)
        db.session.commit()
        flash('Goal updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating goal: {str(e)}', 'error')
    return redirect(url_for('student.goals'))

@student.route('/student/assignment/<int:assignment_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=assignment.course_id,
        status='enrolled'
    ).first_or_404()
    
    if 'submission_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('student.view_assignment', assignment_id=assignment_id))
    
    file = request.files['submission_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('student.view_assignment', assignment_id=assignment_id))
    
    if file:
        filename = secure_filename(file.filename)
        submission_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'submissions', filename)
        os.makedirs(os.path.dirname(submission_path), exist_ok=True)
        file.save(submission_path)
        
        # Check for existing submission
        existing_submission = AssignmentSubmission.query.filter_by(
            student_id=current_user.id,
            assignment_id=assignment_id
        ).first()
        
        if existing_submission:
            existing_submission.submission_file = filename
            existing_submission.submitted_at = datetime.utcnow()
            existing_submission.status = 'submitted'
            db.session.commit()
        else:
            submission = AssignmentSubmission(
                student_id=current_user.id,
                assignment_id=assignment_id,
                submission_file=filename,
                submitted_at=datetime.utcnow(),
                status='submitted'
            )
            db.session.add(submission)
            db.session.commit()
        
        flash('Assignment submitted successfully', 'success')
        return redirect(url_for('student.view_assignment', assignment_id=assignment_id))
    
    flash('Error uploading file', 'error')
    return redirect(url_for('student.view_assignment', assignment_id=assignment_id))

@student.route('/student/progress')
@login_required
@student_required
def progress():
    # Get enrolled courses
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    # Calculate overall GPA
    academic_records = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        status='enrolled'
    ).all()
    grades = [r.grade for r in academic_records if r.grade is not None]
    overall_gpa = sum(grades) / len(grades) if grades else 0.0

    # Calculate progress for each course
    for course in enrolled_courses:
        # Get current grade
        record = AcademicRecord.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        course.current_grade = record.grade if record and record.grade is not None else None

        # Count assignments
        course.total_assignments = Assignment.query.filter_by(course_id=course.id).count()
        course.completed_assignments = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.course_id == course.id,
            AssignmentSubmission.student_id == current_user.id,
            AssignmentSubmission.status == 'graded'
        ).count()

        # Count exams
        course.total_exams = Exam.query.filter_by(course_id=course.id).count()
        course.completed_exams = ExamGrade.query.join(Exam).filter(
            Exam.course_id == course.id,
            ExamGrade.student_id == current_user.id
        ).count()

        # Count quizzes
        course.total_quizzes = Quiz.query.filter_by(course_id=course.id).count()
        course.completed_quizzes = 0  # You'll need to implement quiz completion tracking

    return render_template('student/progress.html',
                         title='Academic Progress',
                         enrolled_courses=enrolled_courses,
                         overall_gpa=overall_gpa)

@student.route('/student/analytics')
@login_required
@student_required
def analytics():
    # Get enrolled courses
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).all()
    
    course_stats = []
    for course in enrolled_courses:
        # Get student's grades
        assignment_grades = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.course_id == course.id,
            AssignmentSubmission.student_id == current_user.id,
            AssignmentSubmission.status == 'graded'
        ).with_entities(AssignmentSubmission.grade).all()
        
        exam_grades = ExamGrade.query.join(Exam).filter(
            Exam.course_id == course.id,
            ExamGrade.student_id == current_user.id
        ).with_entities(ExamGrade.grade).all()
        
        all_grades = [g.grade for g in assignment_grades + exam_grades if g.grade is not None]
        
        if all_grades:
            stats = {
                'course': course,
                'average_grade': sum(all_grades) / len(all_grades),
                'highest_grade': max(all_grades),
                'lowest_grade': min(all_grades),
                'total_grades': len(all_grades)
            }
            course_stats.append(stats)
    
    return render_template('student/analytics.html',
                         title='Performance Analytics',
                         course_stats=course_stats)

@student.route('/student/exam/<int:exam_id>')
@login_required
@student_required
def view_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    exam_grade = ExamGrade.query.filter_by(
        student_id=current_user.id,
        exam_id=exam_id
    ).first()
    return render_template('student/view_exam.html', 
                         exam=exam, 
                         exam_grade=exam_grade)

@student.route('/student/assignments')
@login_required
@student_required
def assignments():
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    assignments = Assignment.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).all()
    
    return render_template('student/assignments.html',
                         title='My Assignments',
                         assignments=assignments,
                         courses=enrolled_courses,
                         now=datetime.utcnow())

@student.route('/student/quizzes')
@login_required
@student_required
def quizzes():
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    quizzes = Quiz.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).all()
    
    return render_template('student/quizzes.html',
                         title='My Quizzes',
                         quizzes=quizzes,
                         courses=enrolled_courses,
                         now=datetime.utcnow())

@student.route('/student/exams')
@login_required
@student_required
def exams():
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    exams = Exam.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).all()
    
    return render_template('student/exams.html',
                         title='My Exams',
                         exams=exams,
                         courses=enrolled_courses,
                         now=datetime.utcnow(),
                         timedelta=timedelta)

@student.route('/student/submissions')
@login_required
@student_required
def submissions():
    submissions = AssignmentSubmission.query.filter_by(
        student_id=current_user.id
    ).order_by(AssignmentSubmission.submitted_at.desc()).all()
    
    return render_template('student/submissions.html',
                         title='My Submissions',
                         submissions=submissions)

@student.route('/student/grades')
@login_required
@student_required
def grades():
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    # Calculate overall GPA
    academic_records = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        status='enrolled'
    ).all()
    grades_list = [r.grade for r in academic_records if r.grade is not None]
    overall_gpa = sum(grades_list) / len(grades_list) if grades_list else 0.0
    
    for course in enrolled_courses:
        # Get assignment grades
        assignment_grades = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.course_id == course.id,
            AssignmentSubmission.student_id == current_user.id,
            AssignmentSubmission.status == 'graded'
        ).all()
        
        # Get exam grades
        exam_grades = ExamGrade.query.join(Exam).filter(
            Exam.course_id == course.id,
            ExamGrade.student_id == current_user.id
        ).all()
        
        # Calculate course grade
        record = AcademicRecord.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        course.current_grade = record.grade if record and record.grade is not None else None
        
        # Prepare grade items list
        grade_items = []
        
        # Add assignments to grade items
        for submission in assignment_grades:
            if hasattr(submission, 'assignment') and submission.assignment:
                grade_items.append({
                    'title': submission.assignment.title,
                    'type': 'assignment',
                    'due_date': submission.assignment.due_date,
                    'grade': submission.grade,
                    'total_points': submission.assignment.total_points,
                    'weight': submission.assignment.weight,
                    'submission_id': submission.id
                })
        
        # Add exams to grade items
        for grade in exam_grades:
            if hasattr(grade, 'exam') and grade.exam:
                grade_items.append({
                    'title': grade.exam.title,
                    'type': grade.exam.exam_type,
                    'due_date': grade.exam.exam_date,
                    'grade': grade.grade,
                    'total_points': grade.exam.total_points,
                    'weight': grade.exam.weight,
                    'exam_id': grade.exam_id
                })
        
        # Sort grade items by due date
        grade_items.sort(key=lambda x: x['due_date'])
        course.grade_items = grade_items
    
    return render_template('student/grades.html',
                         title='My Grades',
                         courses=enrolled_courses,
                         overall_gpa=overall_gpa)

@student.route('/student/academic_progress')
@login_required
@student_required
def academic_progress():
    return redirect(url_for('student.progress'))

@student.route('/student/performance')
@login_required
@student_required
def performance():
    return redirect(url_for('student.analytics'))

@student.route('/student/messages')
@login_required
@student_required
def messages():
    return redirect(url_for('communication.messages'))

@student.route('/student/notifications')
@login_required
@student_required
def notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()
    
    return render_template('student/notifications.html',
                         title='Notifications',
                         notifications=notifications)

@student.route('/student/announcements')
@login_required
@student_required
def announcements():
    # Get announcements for courses the student is enrolled in
    announcements = (Announcement.query
        .join(Course)
        .join(AcademicRecord)
        .filter(
            AcademicRecord.student_id == current_user.id,
            AcademicRecord.status == 'enrolled'
        )
        .order_by(Announcement.created_at.desc())
        .all())
    
    return render_template('student/announcements.html', 
                         announcements=announcements)

@student.route('/student/help')
@login_required
@student_required
def help():
    # Define help categories
    help_categories = [
        {
            'id': 1,
            'name': 'Getting Started',
            'description': 'Learn the basics of using the student portal',
            'icon': 'fas fa-rocket'
        },
        {
            'id': 2,
            'name': 'Courses & Enrollment',
            'description': 'Information about course management and enrollment',
            'icon': 'fas fa-book'
        },
        {
            'id': 3,
            'name': 'Assignments & Exams',
            'description': 'Help with assignments, quizzes, and exams',
            'icon': 'fas fa-tasks'
        },
        {
            'id': 4,
            'name': 'Academic Progress',
            'description': 'Track your academic performance and goals',
            'icon': 'fas fa-chart-line'
        },
        {
            'id': 5,
            'name': 'Technical Support',
            'description': 'Technical issues and troubleshooting',
            'icon': 'fas fa-cogs'
        }
    ]
    
    # Define popular topics
    popular_topics = [
        {
            'id': 1,
            'title': 'How to Submit Assignments',
            'description': 'Step-by-step guide for submitting assignments',
            'category': 'Assignments & Exams'
        },
        {
            'id': 2,
            'title': 'Understanding Your GPA',
            'description': 'Learn how your GPA is calculated',
            'category': 'Academic Progress'
        },
        {
            'id': 3,
            'title': 'Course Registration Guide',
            'description': 'Complete guide to course registration',
            'category': 'Courses & Enrollment'
        }
    ]
    
    return render_template('student/help.html',
                         title='Help Center',
                         help_categories=help_categories,
                         popular_topics=popular_topics)

@student.route('/student/contact')
@login_required
@student_required
def contact():
    return render_template('student/contact.html',
                         title='Contact Support')

@student.route('/student/feedback')
@login_required
@student_required
def feedback():
    return render_template('student/feedback.html',
                         title='Submit Feedback')

@student.route('/student/user_guide')
@login_required
@student_required
def user_guide():
    return render_template('student/user_guide.html', title='User Guide')

@student.route('/student/faqs')
@login_required
@student_required
def faqs():
    return render_template('student/faqs.html', title='FAQs')

@student.route('/student/search_faqs')
@login_required
@student_required
def search_faqs():
    query = request.args.get('q', '')
    # Implement FAQ search logic here
    search_results = []  # Replace with actual search results
    return render_template('student/faqs.html', 
                         title='FAQ Search Results',
                         search_results=search_results,
                         search_query=query)

@student.route('/student/contact_support')
@login_required
@student_required
def contact_support():
    return redirect(url_for('student.contact'))

@student.route('/student/help_topic/<int:topic_id>')
@login_required
@student_required
def help_topic(topic_id):
    # Implement help topic retrieval logic here
    topic = {}  # Replace with actual topic data
    return render_template('student/help_topic.html',
                         title='Help Topic',
                         topic=topic)

@student.route('/student/help_category/<int:category_id>')
@login_required
@student_required
def help_category(category_id):
    # Implement help category retrieval logic here
    category = {}  # Replace with actual category data
    topics = []  # Replace with actual topics data
    return render_template('student/help_category.html',
                         title='Help Category',
                         category=category,
                         topics=topics)

@student.route('/student/search_help')
@login_required
@student_required
def search_help():
    query = request.args.get('q', '')
    # Implement help search logic here
    search_results = []  # Replace with actual search results
    return render_template('student/help.html',
                         title='Help Search Results',
                         search_results=search_results,
                         search_query=query)

@student.route('/student/schedule')
@login_required
@student_required
def schedule():
    # Get all enrolled courses for the student using the proper query
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()

    # Initialize list to store all schedule items
    schedule_items = []

    # Get current datetime for status comparison
    now = datetime.utcnow()

    for course in enrolled_courses:
        # Add assignments
        for assignment in course.assignments:
            status = get_item_status(assignment.due_date, now)
            schedule_items.append({
                'type': 'Assignment',
                'title': assignment.title,
                'description': assignment.description,
                'date': assignment.due_date,
                'course': course,
                'status': status
            })
        
        # Add exams
        for exam in course.exams:
            status = get_item_status(exam.exam_date, now)
            schedule_items.append({
                'type': 'Exam',
                'title': exam.title,
                'description': f'Exam for {course.name}',
                'date': exam.exam_date,
                'course': course,
                'status': status
            })
        
        # Add quizzes
        for quiz in course.quizzes:
            # Handle quizzes with no due_date
            if quiz.due_date is not None:
                status = get_item_status(quiz.due_date, now)
                date_value = quiz.due_date
            else:
                status = 'Date Not Set'
                date_value = None
            schedule_items.append({
                'type': 'Quiz',
                'title': quiz.title,
                'description': f'Quiz for {course.name}',
                'date': date_value,
                'course': course,
                'status': status
            })

    # Sort all items by date; items with None date go last
    schedule_items.sort(key=lambda x: (x['date'] is None, x['date']))

    return render_template('student/schedule.html',
                         title='Course Schedule',
                         schedule_items=schedule_items)

def get_item_status(date, now):
    """Helper function to determine the status of a schedule item."""
    if date < now:
        return 'Past Due'
    elif date < now + timedelta(days=7):
        return 'Upcoming'
    else:
        return 'Pending'

@student.route('/student/courses')
@login_required
@student_required
def courses():
    # Get enrolled courses with their academic records
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    # Get academic records for grades
    for course in enrolled_courses:
        record = AcademicRecord.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        course.grade = record.grade if record else None
    
    return render_template('student/courses.html',
                         title='My Courses',
                         courses=enrolled_courses)

@student.route('/student/material/<int:material_id>')
@login_required
@student_required
def download_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=material.course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get the file path
    file_path = os.path.join(current_app.root_path, 'static', material.file_path)
    
    if not os.path.exists(file_path):
        flash('Material file not found', 'error')
        return redirect(url_for('student.course_materials', course_id=material.course_id))
    
    return send_file(file_path,
                    as_attachment=True,
                    download_name=os.path.basename(material.file_path))

@student.route('/student/course/<int:course_id>/schedule')
@login_required
@student_required
def course_schedule(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get all scheduled items for this course
    assignments = Assignment.query.filter_by(course_id=course_id).order_by(Assignment.due_date).all()
    exams = Exam.query.filter_by(course_id=course_id).order_by(Exam.exam_date).all()
    
    # Combine all scheduled items
    schedule_items = []
    
    # Add assignments to schedule
    for assignment in assignments:
        schedule_items.append({
            'type': 'Assignment',
            'title': assignment.title,
            'date': assignment.due_date,
            'description': assignment.description,
            'status': 'Pending' if assignment.due_date > datetime.utcnow() else 'Past Due'
        })
    
    # Add exams to schedule
    for exam in exams:
        schedule_items.append({
            'type': 'Exam',
            'title': exam.title,
            'date': exam.exam_date,
            'description': exam.description,
            'status': 'Upcoming' if exam.exam_date > datetime.utcnow() else 'Completed'
        })
    
    # Sort all items by date
    schedule_items.sort(key=lambda x: x['date'])
    
    return render_template('student/course_schedule.html',
                         title=f'{course.name} - Schedule',
                         course=course,
                         schedule_items=schedule_items,
                         now=datetime.utcnow())

@student.route('/student/assignment/<int:assignment_id>')
@login_required
@student_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = AssignmentSubmission.query.filter_by(
        student_id=current_user.id,
        assignment_id=assignment_id
    ).first()
    return render_template('student/view_assignment.html', 
                         assignment=assignment, 
                         submission=submission,
                         now=datetime.utcnow())

@student.route('/student/goals/add', methods=['POST'])
@login_required
@student_required
def add_goal():
    title = request.form.get('title')
    description = request.form.get('description')
    target_date = datetime.strptime(request.form.get('target_date'), '%Y-%m-%d')
    
    goal = AcademicGoal(
        student_id=current_user.id,
        title=title,
        description=description,
        target_date=target_date,
        status='in_progress'
    )
    
    db.session.add(goal)
    db.session.commit()
    
    flash('Academic goal added successfully!', 'success')
    return redirect(url_for('student.goals'))


@student.route('/student/goal/<int:goal_id>/delete', methods=['POST'])
@login_required
@student_required
def delete_goal(goal_id):
    goal = AcademicGoal.query.get_or_404(goal_id)
    if goal.student_id != current_user.id:
        flash('You do not have permission to delete this goal.', 'error')
        return redirect(url_for('student.goals'))
    try:
        db.session.delete(goal)
        db.session.commit()
        flash('Academic goal deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting goal: {str(e)}', 'error')
    return redirect(url_for('student.goals')) 

@student.route('/student/new_message')
@login_required
@student_required
def new_message():
    return redirect(url_for('communication.messages'))

@student.route('/student/view_message/<int:message_id>')
@login_required
@student_required
def view_message(message_id):
    return redirect(url_for('communication.messages'))

@student.route('/student/reply_message/<int:message_id>')
@login_required
@student_required
def reply_message(message_id):
    return redirect(url_for('communication.messages'))

@student.route('/student/send_message', methods=['POST'])
@login_required
@student_required
def send_message():
    return redirect(url_for('communication.send_message'))

@student.route('/student/delete_message/<int:message_id>')
@login_required
@student_required
def delete_message(message_id):
    return redirect(url_for('communication.messages')) 

@student.route('/student/course/<int:course_id>/discussions')
@login_required
@student_required
def course_discussions(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    discussions = Discussion.query.filter_by(course_id=course_id).order_by(Discussion.created_at.desc()).all()
    
    return render_template('communication/discussions.html',
                         course=course,
                         discussions=discussions,
                         course_id=course_id)

@student.route('/student/discussion/<int:discussion_id>')
@login_required
@student_required
def discussion_detail(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    
    # Verify enrollment in the course
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=discussion.course_id,
        status='enrolled'
    ).first_or_404()
    
    posts = discussion.posts.order_by(DiscussionPost.created_at).all()
    
    return render_template('communication/discussion_detail.html',
                         discussion=discussion,
                         posts=posts)

@student.route('/student/discussion/<int:discussion_id>/post', methods=['POST'])
@login_required
@student_required
def add_discussion_post(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    
    # Verify enrollment in the course
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=discussion.course_id,
        status='enrolled'
    ).first_or_404()
    
    content = request.form.get('content')
    content_type = request.form.get('content_type', 'text')
    parent_id = request.form.get('parent_id')
    
    if not content:
        flash('Post content is required.', 'error')
        return redirect(url_for('student.discussion_detail', discussion_id=discussion_id))
    
    post = DiscussionPost(
        content=content,
        content_type=content_type,
        discussion_id=discussion_id,
        author_id=current_user.id,
        parent_id=parent_id if parent_id else None
    )
    
    db.session.add(post)
    
    # Handle attachments
    files = request.files.getlist('attachments[]')
    print(f"Processing {len(files)} files for discussion post")
    
    for file in files:
        print(f"Processing file: {file.filename}, type: {file.content_type}")
        attachment = save_attachment(file)
        if attachment:
            print(f"Created attachment: {attachment.filename}, path: {attachment.file_path}")
            attachment.discussion_post = post
            db.session.add(attachment)
        else:
            print(f"Failed to create attachment for file: {file.filename}")
    
    db.session.commit()
    
    flash('Your post has been added.', 'success')
    return redirect(url_for('student.discussion_detail', discussion_id=discussion_id))

@student.route('/student/course/<int:course_id>/create_discussion', methods=['POST'])
@login_required
@student_required
def create_discussion(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        flash('Both title and content are required.', 'error')
        return redirect(url_for('student.course_discussions', course_id=course_id))
    
    discussion = Discussion(
        title=title,
        course_id=course_id,
        created_by=current_user.id
    )
    db.session.add(discussion)
    db.session.commit()
    
    # Create the initial post
    post = DiscussionPost(
        content=content,
        discussion_id=discussion.id,
        author_id=current_user.id
    )
    db.session.add(post)
    db.session.commit()
    
    flash('Discussion created successfully.', 'success')
    return redirect(url_for('student.discussion_detail', discussion_id=discussion.id)) 

@student.route('/student/discussion/attachment/<int:attachment_id>')
@login_required
@student_required
def download_discussion_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Verify that the user has access to this attachment
    if attachment.discussion_post:
        # Check if user is enrolled in the course
        enrollment = AcademicRecord.query.filter_by(
            student_id=current_user.id,
            course_id=attachment.discussion_post.discussion.course_id,
            status='enrolled'
        ).first_or_404()
        
        # Get the file path
        file_path = os.path.join(current_app.root_path, 'static', attachment.file_path)
        
        if not os.path.exists(file_path):
            flash('Attachment file not found', 'error')
            return redirect(url_for('student.discussion_detail', discussion_id=attachment.discussion_post.discussion_id))
        
        return send_file(file_path,
                        as_attachment=True,
                        download_name=attachment.filename)
    
    return abort(404) 

@student.route('/student/semester-goals')
@login_required
@student_required
def semester_goals():
    # Get current semester goals
    semester_goal = SemesterGoal.query.filter_by(
        student_id=current_user.id
    ).order_by(SemesterGoal.id.desc()).first()
    
    # Get module goals if semester goal exists
    module_goals = []
    if semester_goal:
        module_goals = ModuleGoal.query.filter_by(
            semester_goal_id=semester_goal.id
        ).all()
        
        # Calculate progress for each module goal
        for goal in module_goals:
            goal.progress = calculate_module_progress(goal)
    
    # Get enrolled courses for setting new goals
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    # Get current academic year
    current_academic_year = datetime.now().year
    if datetime.now().month < 8:  # If before August, use previous year
        current_academic_year -= 1
    
    return render_template(
        'student/semester_goals.html',
        semester_goal=semester_goal,
        module_goals=module_goals,
        enrolled_courses=enrolled_courses,
        current_academic_year=current_academic_year
    )

def calculate_current_gpa():
    """Calculate current GPA based on all completed assessments."""
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    total_credits = 0
    weighted_grades = 0
    
    for course in enrolled_courses:
        course_total = 0
        total_weight = 0
        
        # Get completed assignments
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        for assignment in assignments:
            submission = AssignmentSubmission.query.filter_by(
                student_id=current_user.id,
                assignment_id=assignment.id,
                status='graded'
            ).first()
            
            if submission and submission.grade is not None:
                course_total += submission.grade * (assignment.weight / 100)
                total_weight += assignment.weight
        
        # Get completed quizzes
        quizzes = Quiz.query.filter_by(course_id=course.id).all()
        for quiz in quizzes:
            submission = QuizSubmission.query.filter_by(
                student_id=current_user.id,
                quiz_id=quiz.id,
                status='completed'
            ).first()
            
            if submission and submission.score is not None:
                course_total += submission.score * (quiz.weight / 100)
                total_weight += quiz.weight
        
        # Get exam grades
        exams = Exam.query.filter_by(course_id=course.id).all()
        for exam in exams:
            grade = ExamGrade.query.filter_by(
                student_id=current_user.id,
                exam_id=exam.id
            ).first()
            
            if grade and grade.score is not None:
                course_total += grade.score * (exam.weight / 100)
                total_weight += exam.weight
        
        # Calculate course grade if there are any graded assessments
        if total_weight > 0:
            course_grade = course_total * (100 / total_weight)  # Scale to 100%
            # Convert to 4.0 scale
            gpa_grade = (course_grade / 100) * 4.0
            
            weighted_grades += gpa_grade * course.credits
            total_credits += course.credits
    
    return weighted_grades / total_credits if total_credits > 0 else 0

@student.route('/student/semester-goals/set', methods=['POST'])
@login_required
@student_required
def set_semester_goals():
    # Create new semester goal
    current_gpa = calculate_current_gpa()
    semester_goal = SemesterGoal(
        student_id=current_user.id,
        academic_year=request.form['academic_year'],
        semester=request.form['semester'],
        target_gpa=float(request.form['target_gpa']),
        current_gpa=current_gpa
    )
    db.session.add(semester_goal)
    db.session.flush()  # Get the ID of the semester goal
    
    # Create module goals
    course_ids = request.form.getlist('course_ids[]')
    module_targets = request.form.getlist('module_targets[]')
    
    for course_id, target in zip(course_ids, module_targets):
        # Calculate current grade for this course
        submissions = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.course_id == int(course_id),
            AssignmentSubmission.student_id == current_user.id,
            AssignmentSubmission.status == 'graded'
        ).all()
        
        current_grade = (
            sum(s.grade for s in submissions) / len(submissions)
            if submissions else 0
        )
        
        module_goal = ModuleGoal(
            semester_goal_id=semester_goal.id,
            course_id=int(course_id),
            target_grade=float(target),
            current_grade=current_grade
        )
        db.session.add(module_goal)
    
    try:
        db.session.commit()
        flash('Semester goals set successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error setting semester goals. Please try again.', 'error')
        current_app.logger.error(f'Error setting semester goals: {str(e)}')
    
    return redirect(url_for('student.semester_goals'))

@student.route('/student/semester-goals/module/<int:goal_id>/update', methods=['POST'])
@login_required
@student_required
def update_module_goal(goal_id):
    goal = ModuleGoal.query.get_or_404(goal_id)
    
    # Verify ownership
    if goal.semester_goal.student_id != current_user.id:
        abort(403)
    
    try:
        # Update module goal target grade
        goal.target_grade = float(request.form['target_grade'])
        
        # Calculate and update current grade for this module
        course_total = 0
        total_weight = 0
        
        # Get completed assignments
        assignments = Assignment.query.filter_by(course_id=goal.course_id).all()
        for assignment in assignments:
            submission = AssignmentSubmission.query.filter_by(
                student_id=current_user.id,
                assignment_id=assignment.id,
                status='graded'
            ).first()
            
            if submission and submission.grade is not None:
                course_total += submission.grade * (assignment.weight / 100)
                total_weight += assignment.weight
        
        # Get completed quizzes
        quizzes = Quiz.query.filter_by(course_id=goal.course_id).all()
        for quiz in quizzes:
            submission = QuizSubmission.query.filter_by(
                student_id=current_user.id,
                quiz_id=quiz.id,
                status='completed'
            ).first()
            
            if submission and submission.score is not None:
                course_total += submission.score * (quiz.weight / 100)
                total_weight += quiz.weight
        
        # Get exam grades
        exams = Exam.query.filter_by(course_id=goal.course_id).all()
        for exam in exams:
            grade = ExamGrade.query.filter_by(
                student_id=current_user.id,
                exam_id=exam.id
            ).first()
            
            if grade and grade.score is not None:
                course_total += grade.score * (exam.weight / 100)
                total_weight += exam.weight
        
        # Update current grade if there are any graded assessments
        if total_weight > 0:
            goal.current_grade = course_total * (100 / total_weight)
        
        # Update semester goal's current GPA
        goal.semester_goal.current_gpa = calculate_current_gpa()
        
        db.session.commit()
        flash('Module goal updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating module goal. Please try again.', 'error')
        current_app.logger.error(f'Error updating module goal: {str(e)}')
    
    return redirect(url_for('student.semester_goals'))

def calculate_module_progress(goal):
    """Calculate progress and required scores for a module goal."""
    course = goal.course
    total_weight = 0
    completed_weight = 0
    current_score = 0
    
    # Get all assessments
    assignments = Assignment.query.filter_by(course_id=course.id).all()
    quizzes = Quiz.query.filter_by(course_id=course.id).all()
    exams = Exam.query.filter_by(course_id=course.id).all()
    
    completed = []
    remaining = []
    
    # Process assignments
    for assignment in assignments:
        total_weight += assignment.weight
        submission = AssignmentSubmission.query.filter_by(
            student_id=current_user.id,
            assignment_id=assignment.id,
            status='graded'
        ).first()
        
        if submission and submission.grade is not None:
            completed.append({
                'type': 'assignment',
                'item': assignment,
                'grade': submission.grade
            })
            completed_weight += assignment.weight
            current_score += submission.grade * (assignment.weight / 100)
        else:
            remaining.append({
                'type': 'assignment',
                'item': assignment
            })
    
    # Process quizzes
    for quiz in quizzes:
        total_weight += quiz.weight
        submission = QuizSubmission.query.filter_by(
            student_id=current_user.id,
            quiz_id=quiz.id,
            status='completed'
        ).first()
        
        if submission and submission.score is not None:
            completed.append({
                'type': 'quiz',
                'item': quiz,
                'grade': submission.score
            })
            completed_weight += quiz.weight
            current_score += submission.score * (quiz.weight / 100)
        else:
            remaining.append({
                'type': 'quiz',
                'item': quiz
            })
    
    # Process exams
    for exam in exams:
        total_weight += exam.weight
        grade = ExamGrade.query.filter_by(
            student_id=current_user.id,
            exam_id=exam.id
        ).first()
        
        if grade and grade.score is not None:
            completed.append({
                'type': 'exam',
                'item': exam,
                'grade': grade.score
            })
            completed_weight += exam.weight
            current_score += grade.score * (exam.weight / 100)
        else:
            remaining.append({
                'type': 'exam',
                'item': exam
            })
    
    # Calculate required score for remaining assessments
    remaining_weight = total_weight - completed_weight
    if remaining_weight > 0:
        target_total = goal.target_grade * (total_weight / 100)
        current_total = current_score * (total_weight / 100)
        required_score = ((target_total - current_total) / remaining_weight) * 100
        
        # Calculate projected grade based on current performance
        if completed:
            avg_performance = sum(c['grade'] for c in completed) / len(completed)
            projected_grade = (
                (current_score * completed_weight + 
                 avg_performance * remaining_weight) / total_weight
            )
        else:
            projected_grade = None
    else:
        required_score = 0
        projected_grade = current_score
    
    return {
        'completed_weight': completed_weight,
        'total_weight': total_weight,
        'current_score': current_score,
        'required_score': required_score,
        'projected_grade': projected_grade,
        'remaining_assessments': remaining,
        'completed_assessments': completed
    }

def suggest_module_goals(target_gpa, courses):
    """Suggest module goals based on semester GPA target."""
    # Convert GPA to percentage (assuming 4.0 = 100%)
    target_percentage = (target_gpa / 4.0) * 100
    
    # Get student's historical performance in each course type
    course_type_performance = {}
    for course in courses:
        # Get previous grades in similar courses
        similar_courses = AcademicRecord.query.join(Course).filter(
            AcademicRecord.student_id == current_user.id,
            Course.code.startswith(course.code[:3]),  # Same subject
            AcademicRecord.grade.isnot(None)
        ).all()
        
        if similar_courses:
            avg_grade = sum(r.grade for r in similar_courses) / len(similar_courses)
            course_type_performance[course.id] = avg_grade
        else:
            course_type_performance[course.id] = target_percentage
    
    # Adjust goals based on historical performance while maintaining target GPA
    total_credits = sum(c.credits for c in courses)
    suggested_goals = {}
    
    # First pass: Set initial goals based on historical performance
    total_weighted_goal = 0
    for course in courses:
        performance_factor = course_type_performance[course.id] / target_percentage
        suggested_goal = target_percentage * performance_factor
        suggested_goal = min(max(suggested_goal, 60), 100)  # Keep between 60% and 100%
        suggested_goals[course.id] = suggested_goal
        total_weighted_goal += suggested_goal * course.credits
    
    # Second pass: Adjust to meet target GPA
    target_total = target_percentage * total_credits
    adjustment_needed = target_total - total_weighted_goal
    if adjustment_needed != 0:
        adjustment_per_credit = adjustment_needed / total_credits
        for course in courses:
            suggested_goals[course.id] += adjustment_per_credit
            suggested_goals[course.id] = min(max(suggested_goals[course.id], 60), 100)
    
    return suggested_goals

@student.route('/student/semester-goals/suggest', methods=['POST'])
@login_required
@student_required
def suggest_goals():
    """Get suggested module goals based on target GPA."""
    target_gpa = float(request.form['target_gpa'])
    
    # Get enrolled courses
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    suggested_goals = suggest_module_goals(target_gpa, enrolled_courses)
    
    return jsonify({
        'suggested_goals': {str(k): float("%.1f" % v) 
                          for k, v in suggested_goals.items()}
    }) 

@student.route('/student/quiz/<int:quiz_id>')
@login_required
@student_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=quiz.course_id,
        status='enrolled'
    ).first_or_404()
    
    # Check if quiz is available
    now = datetime.utcnow()
    if now < quiz.start_time:
        flash('This quiz is not yet available.', 'error')
        return redirect(url_for('student.course_detail', course_id=quiz.course_id))
    
    if now > quiz.end_time:
        flash('This quiz has expired.', 'error')
        return redirect(url_for('student.course_detail', course_id=quiz.course_id))
    
    # Check if already submitted
    submission = quiz.get_submission(current_user.id)
    if submission and submission.status == 'completed':
        flash('You have already completed this quiz.', 'info')
        return redirect(url_for('student.view_quiz_result', quiz_id=quiz_id))
    
    return render_template('student/take_quiz.html',
                         title=f'Take Quiz: {quiz.title}',
                         quiz=quiz)

@student.route('/student/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=quiz.course_id,
        status='enrolled'
    ).first_or_404()
    
    # Check if quiz is still available
    now = datetime.utcnow()
    if now > quiz.end_time:
        flash('This quiz has expired.', 'error')
        return redirect(url_for('student.course_detail', course_id=quiz.course_id))
    
    # Process quiz submission
    try:
        # Create or update submission
        submission = QuizSubmission.query.filter_by(
            student_id=current_user.id,
            quiz_id=quiz_id
        ).first()
        
        if submission:
            submission.score = float(request.form.get('score', 0))
            submission.status = 'completed'
            submission.submitted_at = now
        else:
            submission = QuizSubmission(
                quiz_id=quiz_id,
                student_id=current_user.id,
                score=float(request.form.get('score', 0)),
                status='completed',
                submitted_at=now
            )
            db.session.add(submission)
        
        db.session.commit()
        flash('Quiz submitted successfully!', 'success')
        return redirect(url_for('student.view_quiz_result', quiz_id=quiz_id))
    
    except Exception as e:
        db.session.rollback()
        flash('Error submitting quiz. Please try again.', 'error')
        return redirect(url_for('student.take_quiz', quiz_id=quiz_id))

@student.route('/student/quiz/<int:quiz_id>/result')
@login_required
@student_required
def view_quiz_result(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    submission = quiz.get_submission(current_user.id)
    
    if not submission:
        flash('You have not taken this quiz yet.', 'error')
        return redirect(url_for('student.course_detail', course_id=quiz.course_id))
    
    return render_template('student/quiz_result.html',
                         title=f'Quiz Result: {quiz.title}',
                         quiz=quiz,
                         submission=submission) 