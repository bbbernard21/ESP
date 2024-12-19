from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial
from datetime import datetime, timedelta

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
    
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    academic_goal = AcademicGoal.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()
    
    return render_template('academic/course_detail.html',
                         title=course.name,
                         course=course,
                         academic_record=academic_record,
                         materials=materials,
                         academic_goal=academic_goal)

@academic.route('/goals', methods=['GET', 'POST'])
@login_required
def goals():
    if request.method == 'POST':
        try:
            target_grade = float(request.form['target_grade'])
            if target_grade < 0 or target_grade > 4:
                flash('Target grade must be between 0 and 4.', 'error')
                return redirect(url_for('academic.goals'))

            goal = AcademicGoal(
                student_id=current_user.id,
                course_id=request.form['course_id'],
                target_grade=target_grade,
                description=request.form['description'],
                deadline=datetime.utcnow() + timedelta(days=90),  # Default deadline of 90 days
                status='active'
            )
            db.session.add(goal)
            db.session.commit()
            flash('Academic goal has been set!', 'success')
        except ValueError:
            flash('Invalid target grade value.', 'error')
        except Exception as e:
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