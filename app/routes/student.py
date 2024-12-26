from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.academic import Course, AcademicRecord, AcademicGoal, Assignment, AssignmentSubmission, Exam, ExamGrade
from app.models.user import User, UserRole
from app.decorators import student_required
from datetime import datetime
from werkzeug.utils import secure_filename
import os

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
                         recent_activities=recent_activities)

@student.route('/student/course/<int:course_id>')
@login_required
@student_required
def course_details(course_id):
    # Verify enrollment
    enrollment = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        status='enrolled'
    ).first_or_404()
    
    course = Course.query.get_or_404(course_id)
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    exams = Exam.query.filter_by(course_id=course_id).all()
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    # Get student's grades for this course
    assignment_submissions = {
        s.assignment_id: s for s in AssignmentSubmission.query.filter_by(
            student_id=current_user.id
        ).all()
    }
    
    exam_grades = {
        g.exam_id: g for g in ExamGrade.query.filter_by(
            student_id=current_user.id
        ).all()
    }
    
    return render_template('student/course_details.html',
                         title=course.name,
                         course=course,
                         assignments=assignments,
                         exams=exams,
                         materials=materials,
                         submissions=assignment_submissions,
                         exam_grades=exam_grades)

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