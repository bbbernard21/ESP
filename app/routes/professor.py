from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models.academic import (
    Course, Assignment, AssignmentSubmission, Exam, ExamGrade, 
    CourseMaterial, AcademicRecord, Quiz, QuizSubmission
)
from app.models.communication import Message, Announcement, Notification
from app.models.user import User, UserRole
from app.decorators import professor_required
from datetime import datetime
from werkzeug.utils import secure_filename
import os

professor = Blueprint('professor', __name__)

# Context processor to inject professor's courses
@professor.app_context_processor
def inject_professor_courses():
    from flask_login import current_user
    from app.models.academic import Course
    courses = []
    try:
        if hasattr(current_user, 'id') and getattr(current_user, 'is_authenticated', False):
            courses = Course.query.filter_by(professor_id=current_user.id).all()
    except Exception:
        pass
    return dict(professor_courses=courses)

# Dashboard
@professor.route('/professor/dashboard')
@login_required
@professor_required
def dashboard():
    # Get courses taught by the professor
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    
    # Calculate total students
    total_students = AcademicRecord.query.join(Course).filter(
        Course.professor_id == current_user.id,
        AcademicRecord.status == 'enrolled'
    ).count()
    
    # Get pending tasks
    pending_tasks = []
    
    # Get ungraded submissions
    ungraded_submissions = AssignmentSubmission.query.join(Assignment).join(Course).filter(
        Course.professor_id == current_user.id,
        AssignmentSubmission.status == 'submitted'
    ).all()
    
    for submission in ungraded_submissions:
        pending_tasks.append({
            'type': 'Grade Assignment',
            'course': submission.assignment.course,
            'title': submission.assignment.title,
            'due_date': datetime.utcnow(),  # Grade as soon as possible
            'action_url': url_for('professor.grade_submission', submission_id=submission.id),
            'action_text': 'Grade'
        })
    
    # Get upcoming exams
    upcoming_exams = Exam.query.join(Course).filter(
        Course.professor_id == current_user.id,
        Exam.exam_date > datetime.utcnow()
    ).order_by(Exam.exam_date).all()
    
    for exam in upcoming_exams:
        pending_tasks.append({
            'type': 'Upcoming Exam',
            'course': exam.course,
            'title': exam.title,
            'due_date': exam.exam_date,
            'action_url': url_for('professor.exams'),
            'action_text': 'View'
        })
    
    # Sort tasks by due date
    pending_tasks.sort(key=lambda x: x['due_date'])
    
    # Get course statistics
    for course in courses:
        # Count enrolled students
        course.enrolled_students = AcademicRecord.query.filter_by(
            course_id=course.id,
            status='enrolled'
        ).count()
        
        # Calculate average grade
        submissions = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.course_id == course.id,
            AssignmentSubmission.status == 'graded'
        ).all()
        
        grades = [s.grade for s in submissions if s.grade is not None]
        course.average_grade = sum(grades) / len(grades) if grades else 0
        
        # Count pending assignments
        course.pending_assignments = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.course_id == course.id,
            AssignmentSubmission.status == 'submitted'
        ).count()
        
        # Get next scheduled class (placeholder - implement based on your schedule model)
        course.next_class = "TBD"
    
    # Get recent submissions
    recent_submissions = AssignmentSubmission.query.join(Assignment).join(Course).filter(
        Course.professor_id == current_user.id
    ).order_by(AssignmentSubmission.submitted_at.desc()).limit(5).all()
    
    # Get recent messages from conversations (same as inbox)
    from app.models.communication import Conversation
    recent_messages = []
    direct_conversations = (Conversation.query
        .filter(
            (Conversation.user1_id == current_user.id) |
            (Conversation.user2_id == current_user.id)
        )
        .order_by(Conversation.updated_at.desc())
        .limit(5)
        .all())
    for convo in direct_conversations:
        # Get the latest message in the conversation
        last_msg = convo.messages.order_by(Message.timestamp.desc()).first()
        if last_msg:
            recent_messages.append(last_msg)
    
    # Get announcements
    announcements = Announcement.query.join(Course).filter(
        Course.professor_id == current_user.id
    ).order_by(Announcement.created_at.desc()).all()
    
    return render_template('professor/dashboard.html',
                         title='Professor Dashboard',
                         courses=courses,
                         total_students=total_students,
                         pending_tasks=pending_tasks,
                         announcements=announcements,
                         recent_submissions=recent_submissions,
                         recent_messages=recent_messages)

# Course Management

@professor.route('/professor/course/<int:course_id>/quiz/create', methods=['GET', 'POST'])
@login_required
@professor_required
def create_quiz(course_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to create quizzes for this course.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    if request.method == 'POST':
        try:
            quiz = Quiz(
                course_id=course_id,
                title=request.form['title'],
                description=request.form.get('description', ''),
                total_marks=float(request.form.get('total_marks', 100)),
                duration=int(request.form.get('duration', 30)),
                start_time=datetime.strptime(request.form['start_time'], '%Y-%m-%d %H:%M'),
                end_time=datetime.strptime(request.form['end_time'], '%Y-%m-%d %H:%M'),
                weight=float(request.form.get('weight', 1.0))
            )
            db.session.add(quiz)
            db.session.commit()
            flash('Quiz created successfully!', 'success')
            return redirect(url_for('professor.course_details', course_id=course_id))
        except Exception as e:
            flash(f'Error creating quiz: {str(e)}', 'error')
    
    return render_template('professor/create_quiz.html',
                         title='Create Quiz',
                         course=course)

@professor.route('/professor/course_materials')
@login_required
@professor_required
def course_materials():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/course_materials.html',
                         title='Course Materials',
                         courses=courses)

@professor.route('/professor/student_enrollments')
@login_required
@professor_required
def student_enrollments():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/student_enrollments.html',
                         title='Student Enrollments',
                         courses=courses)

# Assessment Management
@professor.route('/professor/assignments')
@login_required
@professor_required
def assignments():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/assignments.html',
                         title='Assignments',
                         courses=courses)

@professor.route('/professor/quizzes')
@login_required
@professor_required
def quizzes():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/quizzes.html',
                         title='Quizzes',
                         courses=courses)

@professor.route('/professor/exams')
@login_required
@professor_required
def exams():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/exams.html',
                         title='Exams',
                         courses=courses)

@professor.route('/professor/grade_submissions')
@login_required
@professor_required
def grade_submissions():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    submissions = AssignmentSubmission.query.join(Assignment).filter(
        Assignment.course_id.in_([c.id for c in courses]),
        AssignmentSubmission.status == 'submitted'
    ).order_by(AssignmentSubmission.submitted_at.desc()).all()
    return render_template('professor/grade_submissions.html',
                         title='Grade Submissions',
                         submissions=submissions)

@professor.route('/professor/reevaluation_requests')
@login_required
@professor_required
def reevaluation_requests():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/reevaluation_requests.html',
                         title='Re-evaluation Requests')

# Student Progress
@professor.route('/professor/student_progress')
@login_required
@professor_required
def student_progress():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/student_progress.html',
                         title='Student Progress',
                         courses=courses)



@professor.route('/professor/analytics')
@login_required
@professor_required
def analytics():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    course_stats = []
    for course in courses:
        records = AcademicRecord.query.filter_by(course_id=course.id).all()
        grades = [r.grade for r in records if r.grade is not None]
        if grades:
            stats = {
                'course': course,
                'average_grade': sum(grades) / len(grades),
                'highest_grade': max(grades),
                'lowest_grade': min(grades),
                'passing_rate': len([g for g in grades if g >= 60]) / len(grades) * 100,
                'total_students': len(grades)
            }
            course_stats.append(stats)
    return render_template('professor/analytics.html',
                         title='Analytics & Reports',
                         course_stats=course_stats)

@professor.route('/professor/early_warning', methods=['GET', 'POST'], endpoint='early_warning')
@login_required
@professor_required
def early_warning():
    from flask import session
    from app.utils.early_warning import check_all_students_and_alert
    results = []
    if request.method == 'POST':
        results = check_all_students_and_alert()
        session['early_warning_results'] = results
        flash(f'Early warning check complete. {len(results)} students flagged.', 'info')
    else:
        results = session.get('early_warning_results', [])
    return render_template('professor/early_warning.html', results=results)

# Communication

@professor.route('/professor/announcement/<int:announcement_id>')
@login_required
@professor_required
def get_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    if announcement.course.professor_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    return jsonify({
        'id': announcement.id,
        'course_id': announcement.course_id,
        'title': announcement.title,
        'content': announcement.content
    })

@professor.route('/professor/announcement/<int:announcement_id>/update', methods=['PUT'])
@login_required
@professor_required
def update_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    if announcement.course.professor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    data = request.get_json()
    announcement.title = data.get('title', announcement.title)
    announcement.content = data.get('content', announcement.content)
    announcement.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@professor.route('/professor/announcement/<int:announcement_id>/delete', methods=['DELETE'])
@login_required
@professor_required
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    if announcement.course.professor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    db.session.delete(announcement)
    db.session.commit()
    return jsonify({'success': True})


@professor.route('/professor/course/<int:course_id>/announcement/create', methods=['POST'])
@login_required
@professor_required
def create_announcement(course_id):
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    if not title or not content:
        return jsonify({'success': False, 'error': 'Missing title or content'}), 400
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    announcement = Announcement(
        course_id=course_id,
        title=title,
        content=content,
        created_at=datetime.utcnow(),
        created_by=current_user.id
    )
    db.session.add(announcement)
    db.session.commit()
    return jsonify({'success': True, 'id': announcement.id})

@professor.route('/professor/announcements')
@login_required
@professor_required
def announcements():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/announcements.html',
                         title='Announcements',
                         courses=courses)

@professor.route('/professor/send_notifications')
@login_required
@professor_required
def send_notifications():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return render_template('professor/send_notifications.html',
                         title='Send Notifications',
                         courses=courses)

@professor.route('/professor/messages')
@login_required
@professor_required
def messages():
    from app.models.communication import Conversation, GroupChat, ChatParticipant, ChatMessageRead
    # Get direct conversations for professor
    direct_conversations = (Conversation.query
        .filter(
            (Conversation.user1_id == current_user.id) |
            (Conversation.user2_id == current_user.id)
        )
        .order_by(Conversation.updated_at.desc())
        .all())
    # Get group chats for professor
    group_chats = (GroupChat.query
        .join(ChatParticipant)
        .filter(ChatParticipant.user_id == current_user.id, GroupChat.is_group == True)
        .order_by(GroupChat.created_at.desc())
        .all())
    # All users except current user and admins for new message modal
    available_users = User.query.filter(User.id != current_user.id, User.role != UserRole.ADMIN.value).all()
    return render_template(
        'communication/messages.html',
        base_template='professor/base.html',
        direct_conversations=direct_conversations,
        group_chats=group_chats,
        available_users=available_users,
        ChatMessageRead=ChatMessageRead,
        title='Messages')

# Existing detailed routes
@professor.route('/professor/course/<int:course_id>')
@login_required
@professor_required
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to view this course.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    enrolled_students = User.query.join(AcademicRecord).filter(
        AcademicRecord.course_id == course_id,
        AcademicRecord.status == 'enrolled'
    ).all()
    
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    exams = Exam.query.filter_by(course_id=course_id).all()
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    return render_template('professor/course_details.html',
                         title=course.name,
                         course=course,
                         enrolled_students=enrolled_students,
                         assignments=assignments,
                         quizzes=quizzes,
                         exams=exams,
                         materials=materials)


@professor.route('/professor/course/<int:course_id>/assignment/create', methods=['GET', 'POST'])
@login_required
@professor_required
def create_assignment(course_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to create assignments for this course.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    if request.method == 'POST':
        try:
            assignment = Assignment(
                course_id=course_id,
                title=request.form['title'],
                description=request.form['description'],
                total_points=float(request.form['total_points']),
                weight=float(request.form['weight']),
                due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d')
            )
            db.session.add(assignment)
            db.session.commit()
            flash('Assignment created successfully!', 'success')
            return redirect(url_for('professor.course_details', course_id=course_id))
        except Exception as e:
            flash(f'Error creating assignment: {str(e)}', 'error')
    
    return render_template('professor/create_assignment.html',
                         title='Create Assignment',
                         course=course)

@professor.route('/professor/course/<int:course_id>/exam/create', methods=['GET', 'POST'])
@login_required
@professor_required
def create_exam(course_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to create exams for this course.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    if request.method == 'POST':
        try:
            exam = Exam(
                course_id=course_id,
                title=request.form['title'],
                description=request.form['description'],
                total_points=float(request.form['total_points']),
                exam_type=request.form['exam_type'],
                exam_date=datetime.strptime(request.form['exam_date'], '%Y-%m-%d'),
                duration=int(request.form['duration'])
            )
            db.session.add(exam)
            db.session.commit()
            flash('Exam created successfully!', 'success')
            return redirect(url_for('professor.course_details', course_id=course_id))
        except Exception as e:
            flash(f'Error creating exam: {str(e)}', 'error')
    
    return render_template('professor/create_exam.html',
                         title='Create Exam',
                         course=course)

@professor.route('/professor/course/<int:course_id>/material/upload', methods=['GET', 'POST'])
@login_required
@professor_required
def upload_material(course_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to upload materials for this course.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    if request.method == 'POST':
        try:
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join('uploads', course.code, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                material = CourseMaterial(
                    course_id=course_id,
                    title=request.form['title'],
                    description=request.form['description'],
                    file_path=file_path,
                    material_type=request.form['material_type']
                )
                db.session.add(material)
                db.session.commit()
                flash('Material uploaded successfully!', 'success')
                return redirect(url_for('professor.course_details', course_id=course_id))
        except Exception as e:
            flash(f'Error uploading material: {str(e)}', 'error')
    
    return render_template('professor/upload_material.html',
                         title='Upload Material',
                         course=course)

@professor.route('/professor/grade_submission/<int:submission_id>', methods=['GET', 'POST'])
@login_required
@professor_required
def grade_submission(submission_id):
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    
    # Verify that the professor has permission to grade this submission
    if submission.assignment.course.professor_id != current_user.id:
        flash('You do not have permission to grade this submission.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    if request.method == 'POST':
        try:
            submission.grade = float(request.form['grade'])
            submission.feedback = request.form['feedback']
            submission.status = 'graded'
            submission.graded_at = datetime.utcnow()
            db.session.commit()
            flash('Assignment graded successfully!', 'success')
            return redirect(url_for('professor.grade_submissions'))
        except Exception as e:
            flash(f'Error grading assignment: {str(e)}', 'error')
    
    return render_template('professor/grade_submission.html',
                         title='Grade Submission',
                         submission=submission)

@professor.route('/professor/exam/<int:exam_id>/grade/<int:student_id>', methods=['GET', 'POST'])
@login_required
@professor_required
def grade_exam(exam_id, student_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.course.professor_id != current_user.id:
        flash('You do not have permission to grade this exam.', 'error')
        return redirect(url_for('professor.dashboard'))
    
    if request.method == 'POST':
        try:
            exam_grade = ExamGrade(
                exam_id=exam_id,
                student_id=student_id,
                grade=float(request.form['grade']),
                feedback=request.form['feedback'],
                graded_at=datetime.utcnow()
            )
            db.session.add(exam_grade)
            db.session.commit()
            flash('Exam grade recorded successfully!', 'success')
            return redirect(url_for('professor.course_details', course_id=exam.course_id))
        except Exception as e:
            flash(f'Error recording exam grade: {str(e)}', 'error')
    
    return render_template('professor/grade_exam.html',
                         title='Grade Exam',
                         exam=exam,
                         student=User.query.get_or_404(student_id)) 

@professor.route('/professor/download_material/<int:material_id>')
@login_required
@professor_required
def download_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to download this material.', 'error')
        return redirect(url_for('professor.dashboard'))
    directory = os.path.dirname(material.file_path)
    filename = os.path.basename(material.file_path)
    return send_from_directory(directory, filename, as_attachment=True)

@professor.route('/professor/student_progress/<int:course_id>/<int:student_id>')
@login_required
@professor_required
def student_progress_detail(course_id, student_id):
    course = Course.query.get_or_404(course_id)
    if course.professor_id != current_user.id:
        flash('You do not have permission to view this student\'s progress.', 'error')
        return redirect(url_for('professor.dashboard'))
    student = User.query.get_or_404(student_id)
    record = AcademicRecord.query.filter_by(student_id=student_id, course_id=course_id).first()
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    submissions = AssignmentSubmission.query.filter_by(student_id=student_id).all()
    exams = Exam.query.filter_by(course_id=course_id).all()
    exam_grades = ExamGrade.query.filter_by(student_id=student_id).all()
    return render_template('professor/student_progress_detail.html',
                           course=course, student=student, record=record,
                           assignments=assignments, submissions=submissions,
                           exams=exams, exam_grades=exam_grades)

@professor.route('/professor/help')
@login_required
@professor_required
def help():
    return render_template('professor_help.html')