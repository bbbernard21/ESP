from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial, Assignment, AssignmentSubmission, Exam
from app.models.communication import Notification
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

academic = Blueprint('academic', __name__)

@academic.route('/courses')
@login_required
def courses():
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).all()
    return render_template('academic/courses.html',
                         title='My Courses',
                         courses=enrolled_courses)

@academic.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first_or_404()
    
    # Get course materials
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    # Get assignments
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    # Get exams
    exams = Exam.query.filter_by(course_id=course_id).all()
    
    # Get academic goal
    academic_goal = AcademicGoal.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()
    
    return render_template('academic/course_detail.html',
                         title=f'{course.code} - {course.name}',
                         course=course,
                         academic_record=academic_record,
                         materials=materials,
                         assignments=assignments,
                         exams=exams,
                         academic_goal=academic_goal,
                         now=datetime.utcnow())

@academic.route('/goals', methods=['GET', 'POST'])
@login_required
def goals():
    if request.method == 'POST':
        try:
            # Print form data for debugging
            print("Form data:", request.form)
            
            target_grade = float(request.form['target_grade'])
            if target_grade < 0 or target_grade > 4:
                flash('Target grade must be between 0 and 4.', 'error')
                return redirect(url_for('academic.goals'))

            course = Course.query.get_or_404(request.form['course_id'])
            print(f"Found course: {course.code} - {course.name}")
            
            title = f"Achieve {target_grade} in {course.code}"
            print(f"Creating goal with title: {title}")

            goal = AcademicGoal(
                student_id=current_user.id,
                course_id=course.id,
                title=title,
                target_grade=target_grade,
                description=request.form['description'],
                target_date=datetime.utcnow() + timedelta(days=90),  # Default deadline of 90 days
                status='active'
            )
            print("Created goal object")
            
            db.session.add(goal)
            print("Added goal to session")
            
            db.session.commit()
            print("Committed goal to database")
            
            flash('Academic goal has been set!', 'success')
        except ValueError as ve:
            print(f"ValueError: {str(ve)}")
            flash('Invalid target grade value.', 'error')
        except Exception as e:
            import traceback
            print(f"Error setting goal: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            flash('An error occurred while setting the goal.', 'error')
            db.session.rollback()
        return redirect(url_for('academic.goals'))
    
    # Query goals with course relationship
    academic_goals = AcademicGoal.query.filter_by(
        student_id=current_user.id
    ).order_by(AcademicGoal.created_at.desc()).all()
    
    # Get enrolled courses
    enrolled_courses = Course.query.join(AcademicRecord).filter(
        AcademicRecord.student_id == current_user.id
    ).order_by(Course.code).all()
    
    return render_template('academic/goals.html',
                         title='Academic Goals',
                         goals=academic_goals,
                         courses=enrolled_courses)

@academic.route('/materials/<int:course_id>')
@login_required
def course_materials(course_id):
    course = Course.query.get_or_404(course_id)
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    return render_template('academic/materials.html',
                         title=f'{course.name} - Materials',
                         course=course,
                         materials=materials)

@academic.route('/goal/edit/<int:goal_id>', methods=['POST'])
@login_required
def edit_goal(goal_id):
    goal = AcademicGoal.query.get_or_404(goal_id)
    if goal.student_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('academic.goals'))
    
    try:
        target_grade = float(request.form['target_grade'])
        if target_grade < 0 or target_grade > 4:
            flash('Target grade must be between 0 and 4.', 'error')
            return redirect(url_for('academic.goals'))
        
        goal.target_grade = target_grade
        goal.description = request.form['description']
        goal.status = request.form['status']
        
        db.session.commit()
        flash('Goal has been updated!', 'success')
    except ValueError:
        flash('Invalid target grade value.', 'error')
    except Exception as e:
        flash('An error occurred while updating the goal.', 'error')
        db.session.rollback()
    
    return redirect(url_for('academic.goals'))

@academic.route('/grade_projection/<int:course_id>', methods=['GET', 'POST'])
@login_required
def grade_projection(course_id):
    course = Course.query.get_or_404(course_id)
    academic_record = AcademicRecord.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            current_grade = float(request.form['current_grade'])
            remaining_weight = float(request.form['remaining_weight'])
            target_grade = float(request.form['target_grade'])
            
            # Calculate required grade on remaining assignments
            if remaining_weight > 0:
                # Calculate the weighted sum of completed components
                completed_weight = 100 - remaining_weight
                
                # Calculate required grade for remaining components
                required_grade = ((target_grade * 100) - (current_grade * completed_weight)) / remaining_weight
                
                # Cap the required grade at 100
                required_grade = min(required_grade, 100)
            else:
                required_grade = 0
                
            return jsonify({
                'success': True,
                'required_grade': round(required_grade, 2)
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    # Get academic goal for pre-filling target grade
    academic_goal = AcademicGoal.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()
    
    return render_template('academic/grade_projection.html',
                         title='Grade Projection',
                         course=course,
                         academic_record=academic_record,
                         academic_goal=academic_goal)

@academic.route('/assignment/<int:assignment_id>')
@login_required
def assignment_detail(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment_id,
        student_id=current_user.id
    ).first()
    
    return render_template('academic/assignment_detail.html',
                         title=assignment.title,
                         assignment=assignment,
                         submission=submission)

@academic.route('/assignment/<int:assignment_id>/submit', methods=['POST'])
@login_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    
    try:
        if 'file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('academic.assignment_detail', assignment_id=assignment_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('academic.assignment_detail', assignment_id=assignment_id))
        
        # Save file and create submission
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', 'assignments', str(assignment_id), filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            file_path=file_path
        )
        db.session.add(submission)
        
        # Create notification for submission
        notification = Notification(
            user_id=current_user.id,
            title='Assignment Submitted',
            body=f'You have submitted your assignment for {assignment.title}',
            category='academic'
        )
        db.session.add(notification)
        
        db.session.commit()
        flash('Assignment submitted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while submitting the assignment.', 'error')
    
    return redirect(url_for('academic.assignment_detail', assignment_id=assignment_id)) 