import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Course, AcademicRecord, CourseMaterial, Assignment, Exam, AssignmentSubmission, ExamGrade
from app.models.academic import AcademicGoal
from app.models.communication import Message, Notification, Announcement
from app.models.user import User, UserRole
from app.decorators import student_required
from datetime import datetime
from werkzeug.utils import secure_filename

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
            'action_url': url_for('student.submit_assignment', assignment_id=assignment.id),
            'action_text': 'Submit'
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
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get course materials
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    # Get assignments
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    # Get exams
    exams = Exam.query.filter_by(course_id=course_id).all()
    
    # Calculate course completion percentage
    total_items = len(materials) + len(assignments) + len(exams)
    completed_items = 0
    if total_items > 0:
        # Count completed assignments
        completed_assignments = AssignmentSubmission.query.filter_by(
            student_id=current_user.id,
            status='graded'
        ).join(Assignment).filter(
            Assignment.course_id == course_id
        ).count()
        
        # Count completed exams
        completed_exams = ExamGrade.query.filter_by(
            student_id=current_user.id
        ).join(Exam).filter(
            Exam.course_id == course_id
        ).count()
        
        completed_items = completed_assignments + completed_exams
        course.completion_percentage = (completed_items / total_items) * 100
    else:
        course.completion_percentage = 0
    
    return render_template('student/course_detail.html',
                         title=f'{course.code} - {course.name}',
                         course=course,
                         academic_record=academic_record,
                         materials=materials,
                         assignments=assignments,
                         exams=exams)

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
        student_id=current_user.id,
        status='active'
    ).all()
    
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
        goal.status = request.form['status']
        db.session.commit()
        flash('Goal updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating goal: {str(e)}', 'error')
    
    return redirect(url_for('student.goals'))

@student.route('/student/assignment/<int:assignment_id>/submit', methods=['GET', 'POST'])
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
    
    if request.method == 'POST':
        try:
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join('uploads', 'submissions', str(assignment_id), filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                submission = AssignmentSubmission(
                    assignment_id=assignment_id,
                    student_id=current_user.id,
                    file_path=file_path,
                    submitted_at=datetime.utcnow(),
                    status='submitted'
                )
                db.session.add(submission)
                db.session.commit()
                flash('Assignment submitted successfully!', 'success')
                return redirect(url_for('student.course_details', course_id=assignment.course_id))
        except Exception as e:
            flash(f'Error submitting assignment: {str(e)}', 'error')
    
    return render_template('student/submit_assignment.html',
                         title='Submit Assignment',
                         assignment=assignment)

@student.route('/student/progress')
@login_required
@student_required
def progress():
    # Get all academic records
    academic_records = AcademicRecord.query.filter_by(
        student_id=current_user.id
    ).all()
    
    # Calculate overall GPA
    grades = [r.grade for r in academic_records if r.grade is not None]
    overall_gpa = sum(grades) / len(grades) if grades else 0
    
    # Get progress by course
    course_progress = []
    for record in academic_records:
        course = record.course
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        submissions = AssignmentSubmission.query.filter_by(
            student_id=current_user.id,
            status='graded'
        ).join(Assignment).filter(
            Assignment.course_id == course.id
        ).all()
        
        total_assignments = len(assignments)
        completed_assignments = len(submissions)
        
        progress = {
            'course': course,
            'grade': record.grade,
            'completion_rate': (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
        }
        course_progress.append(progress)
    
    return render_template('student/progress.html',
                         title='Academic Progress',
                         overall_gpa=overall_gpa,
                         course_progress=course_progress)

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
    
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=exam.course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get student's grade if exam is graded
    grade = ExamGrade.query.filter_by(
        exam_id=exam_id,
        student_id=current_user.id
    ).first()
    
    return render_template('student/view_exam.html',
                         title='View Exam',
                         exam=exam,
                         grade=grade)

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
                         courses=enrolled_courses)

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
                         courses=enrolled_courses)

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
                         courses=enrolled_courses)

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
        
        course.grades = {
            'assignments': assignment_grades,
            'exams': exam_grades
        }
    
    return render_template('student/grades.html',
                         title='My Grades',
                         courses=enrolled_courses)

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
    received_messages = Message.query.filter_by(
        recipient_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()
    
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.sent_at.desc()).all()
    
    return render_template('student/messages.html',
                         title='Messages',
                         received_messages=received_messages,
                         sent_messages=sent_messages)

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
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    announcements = Announcement.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).order_by(Announcement.created_at.desc()).all()
    
    return render_template('student/announcements.html',
                         title='Announcements',
                         announcements=announcements,
                         courses=enrolled_courses)

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
    # Get enrolled courses
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    # Get upcoming assignments
    upcoming_assignments = Assignment.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        Assignment.due_date > datetime.utcnow()
    ).order_by(Assignment.due_date).all()
    
    # Get upcoming exams
    upcoming_exams = Exam.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        Exam.exam_date > datetime.utcnow()
    ).order_by(Exam.exam_date).all()
    
    # Get upcoming quizzes
    upcoming_quizzes = Quiz.query.join(Course).join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id,
        Quiz.due_date > datetime.utcnow()
    ).order_by(Quiz.due_date).all()
    
    return render_template('student/schedule.html',
                         title='Course Schedule',
                         courses=enrolled_courses,
                         upcoming_assignments=upcoming_assignments,
                         upcoming_exams=upcoming_exams,
                         upcoming_quizzes=upcoming_quizzes)

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

@student.route('/student/material/<int:material_id>/download')
@login_required
@student_required
def download_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    
    # Verify enrollment
    AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=material.course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get the file path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], material.file_path)
    
    if not os.path.exists(file_path):
        flash('Material file not found.', 'error')
        return redirect(url_for('student.course_materials', course_id=material.course_id))
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=material.file_name
    )

@student.route('/student/course/<int:course_id>/schedule')
@login_required
@student_required
def course_schedule(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment
    AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    # Get assignments
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    # Get exams
    exams = Exam.query.filter_by(course_id=course_id).all()
    
    # Create a list of events for the calendar
    events = []
    
    # Add assignments
    for assignment in assignments:
        events.append({
            'title': f'Assignment: {assignment.title}',
            'start': assignment.due_date.strftime('%Y-%m-%d'),
            'url': url_for('student.view_assignment', assignment_id=assignment.id),
            'className': 'bg-primary'
        })
    
    # Add exams
    for exam in exams:
        events.append({
            'title': f'Exam: {exam.title}',
            'start': exam.exam_date.strftime('%Y-%m-%d'),
            'url': url_for('student.view_exam', exam_id=exam.id),
            'className': 'bg-danger'
        })
    
    return render_template('student/course_schedule.html',
                         title=f'{course.name} - Schedule',
                         course=course,
                         events=events) 