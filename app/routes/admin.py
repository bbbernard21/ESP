from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole
from app.models.academic import Course, Program, AcademicRecord, Assignment, AssignmentSubmission
from app.models.communication import Notification

from app.decorators import admin_required
from datetime import datetime

admin = Blueprint('admin', __name__)

@admin.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_students = User.query.filter_by(role=UserRole.STUDENT.value).count()
    total_professors = User.query.filter_by(role=UserRole.PROFESSOR.value).count()
    total_courses = Course.query.count()
    total_programs = Program.query.count()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Get active courses
    active_courses = Course.query.all()
    
    return render_template('admin/dashboard.html',
                         title='Admin Dashboard',
                         total_users=total_users,
                         total_students=total_students,
                         total_professors=total_professors,
                         total_courses=total_courses,
                         total_programs=total_programs,
                         recent_users=recent_users,
                         active_courses=active_courses)

@admin.route('/admin/profile', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_profile():
    if request.method == 'POST':
        # Update profile info
        current_user.first_name = request.form['first_name']
        current_user.last_name = request.form['last_name']
        current_user.email = request.form['email']
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('admin.admin_profile'))
    return render_template('admin/profile.html', title='Admin Profile')

@admin.route('/admin/change_password', methods=['POST'])
@login_required
@admin_required
def change_admin_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_new_password = request.form['confirm_new_password']
    from werkzeug.security import check_password_hash, generate_password_hash
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('admin.admin_profile'))
    if new_password != confirm_new_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('admin.admin_profile'))
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash('Password changed successfully.', 'success')
    return redirect(url_for('admin.admin_profile'))

@admin.route('/admin/update_preferences', methods=['POST'])
@login_required
@admin_required
def update_admin_preferences():
    current_user.receive_alerts = 'receive_alerts' in request.form
    current_user.enable_2fa = 'enable_2fa' in request.form
    db.session.commit()
    flash('Preferences updated.', 'success')
    return redirect(url_for('admin.admin_profile'))

@admin.route('/admin/logout_other_sessions', methods=['POST'])
@login_required
@admin_required
def logout_other_sessions():
    # For demo: just flash message. Real implementation would revoke all other tokens/sessions.
    flash('Other sessions have been logged out (demo only).', 'info')
    return redirect(url_for('admin.admin_profile'))

@admin.route('/admin/delete_account', methods=['POST'])
@login_required
@admin_required
def delete_admin_account():
    from flask_login import logout_user
    user_id = current_user.id
    logout_user()
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Your admin account has been deleted.', 'warning')
    return redirect(url_for('main.index'))

@admin.route('/admin/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', title='Manage Users', users=users)

@admin.route('/admin/courses')
@login_required
@admin_required
def courses():
    courses = Course.query.all()
    return render_template('admin/courses.html', title='Manage Courses', courses=courses)

@admin.route('/admin/programs')
@login_required
@admin_required
def programs():
    programs = Program.query.all()
    return render_template('admin/programs.html', title='Manage Programs', programs=programs)

@admin.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        try:
            # Validate role
            role = request.form['role']
            if role not in [r.value for r in UserRole]:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('admin.create_user'))

            # Create user
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                role=role
            )
            user.set_password(request.form['password'])

            # If user is a student, assign program and create academic records
            if role == UserRole.STUDENT.value:
                program_id = request.form.get('program_id')
                if not program_id:
                    flash('Program is required for students.', 'error')
                    return redirect(url_for('admin.create_user'))
                
                user.program_id = program_id
                
                # Get current semester and academic year
                current_month = datetime.utcnow().month
                current_year = datetime.utcnow().year
                semester = 'Fall' if 8 <= current_month <= 12 else 'Spring' if 1 <= current_month <= 5 else 'Summer'
                academic_year = f"{current_year}-{current_year+1}" if current_month >= 8 else f"{current_year-1}-{current_year}"

                db.session.add(user)
                db.session.commit()  # Commit to get user.id

                # Enroll in all active courses of the program for current semester
                program_courses = Course.query.filter_by(
                    program_id=program_id,
                    semester=semester,
                    status='active'
                ).all()

                for course in program_courses:
                    academic_record = AcademicRecord(
                        student_id=user.id,
                        course_id=course.id,
                        semester=semester,
                        academic_year=academic_year,
                        status='enrolled'
                    )
                    db.session.add(academic_record)
            else:
                db.session.add(user)

            db.session.commit()
            flash('User created successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating user: ' + str(e), 'error')
    
    programs = Program.query.all()
    return render_template('admin/create_user.html', 
                         title='Create User',
                         roles=[role.value for role in UserRole],
                         programs=programs)

@admin.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Validate role
            role = request.form['role']
            if role not in [r.value for r in UserRole]:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))

            user.username = request.form['username']
            user.email = request.form['email']
            user.first_name = request.form['first_name']
            user.last_name = request.form['last_name']
            
            # Handle role change
            old_role = user.role
            user.role = role
            
            # Handle program assignment for students
            if role == UserRole.STUDENT.value:
                program_id = request.form.get('program_id')
                if not program_id:
                    flash('Program is required for students.', 'error')
                    return redirect(url_for('admin.edit_user', user_id=user_id))
                
                # If program changed, update enrollments
                if user.program_id != int(program_id):
                    user.program_id = program_id
                    
                    # Get current semester and academic year
                    current_month = datetime.utcnow().month
                    current_year = datetime.utcnow().year
                    semester = 'Fall' if 8 <= current_month <= 12 else 'Spring' if 1 <= current_month <= 5 else 'Summer'
                    academic_year = f"{current_year}-{current_year+1}" if current_month >= 8 else f"{current_year-1}-{current_year}"

                    # Remove old enrollments
                    AcademicRecord.query.filter_by(student_id=user.id).delete()

                    # Add new enrollments
                    program_courses = Course.query.filter_by(
                        program_id=program_id,
                        semester=semester,
                        status='active'
                    ).all()

                    for course in program_courses:
                        academic_record = AcademicRecord(
                            student_id=user.id,
                            course_id=course.id,
                            semester=semester,
                            academic_year=academic_year,
                            status='enrolled'
                        )
                        db.session.add(academic_record)
            else:
                user.program_id = None  # Remove program if not a student
                # Remove any existing enrollments
                if old_role == UserRole.STUDENT.value:
                    AcademicRecord.query.filter_by(student_id=user.id).delete()
            
            if request.form.get('password'):
                user.set_password(request.form['password'])
            
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating user: ' + str(e), 'error')
    
    programs = Program.query.all()
    return render_template('admin/edit_user.html', 
                         title='Edit User',
                         user=user,
                         roles=[role.value for role in UserRole],
                         programs=programs)

@admin.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))
        
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    return redirect(url_for('admin.users'))

@admin.route('/admin/create_course', methods=['GET', 'POST'])
@login_required
@admin_required
def create_course():
    if request.method == 'POST':
        try:
            course = Course(
                code=request.form['code'],
                name=request.form['name'],
                description=request.form.get('description'),
                credits=int(request.form['credits']),
                professor_id=request.form.get('professor_id'),
                program_id=request.form.get('program_id'),
                semester=request.form.get('semester'),
                status=request.form.get('status', 'active'),
                assignments_weight=float(request.form.get('assignments_weight', 40)),
                midterm_weight=float(request.form.get('midterm_weight', 25)),
                final_weight=float(request.form.get('final_weight', 35))
            )
            db.session.add(course)
            db.session.commit()
            flash('Course created successfully!', 'success')
            return redirect(url_for('admin.courses'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating course: ' + str(e), 'error')
    
    professors = User.query.filter_by(role=UserRole.PROFESSOR.value).all()
    programs = Program.query.all()
    return render_template('admin/create_course.html',
                         title='Create Course',
                         professors=professors,
                         programs=programs)

@admin.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            course.code = request.form['code']
            course.name = request.form['name']
            course.description = request.form.get('description')
            course.credits = int(request.form['credits'])
            course.professor_id = request.form.get('professor_id')
            course.program_id = request.form.get('program_id')
            course.semester = request.form.get('semester')
            course.status = request.form.get('status', 'active')
            course.assignments_weight = float(request.form.get('assignments_weight', 40))
            course.midterm_weight = float(request.form.get('midterm_weight', 25))
            course.final_weight = float(request.form.get('final_weight', 35))
            
            db.session.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('admin.courses'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating course: ' + str(e), 'error')
    
    professors = User.query.filter_by(role=UserRole.PROFESSOR.value).all()
    programs = Program.query.all()
    return render_template('admin/edit_course.html',
                         title='Edit Course',
                         course=course,
                         professors=professors,
                         programs=programs)

@admin.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    try:
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'error')
    return redirect(url_for('admin.courses'))

@admin.route('/admin/create_program', methods=['GET', 'POST'])
@login_required
@admin_required
def create_program():
    if request.method == 'POST':
        try:
            program = Program(
                code=request.form['code'],
                name=request.form['name'],
                description=request.form.get('description')
            )
            db.session.add(program)
            db.session.commit()
            flash('Program created successfully!', 'success')
            return redirect(url_for('admin.programs'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating program: ' + str(e), 'error')
    
    return render_template('admin/create_program.html', title='Create Program')

@admin.route('/admin/edit_program/<int:program_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_program(program_id):
    program = Program.query.get_or_404(program_id)
    
    if request.method == 'POST':
        try:
            program.code = request.form['code']
            program.name = request.form['name']
            program.description = request.form.get('description')
            
            db.session.commit()
            flash('Program updated successfully!', 'success')
            return redirect(url_for('admin.programs'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating program: ' + str(e), 'error')
    
    return render_template('admin/edit_program.html',
                         title='Edit Program',
                         program=program)

@admin.route('/admin/delete_program/<int:program_id>', methods=['POST'])
@login_required
@admin_required
def delete_program(program_id):
    program = Program.query.get_or_404(program_id)
    try:
        db.session.delete(program)
        db.session.commit()
        flash('Program deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting program: {str(e)}', 'error')
    return redirect(url_for('admin.programs'))

@admin.route('/admin/enroll_student', methods=['GET', 'POST'])
@login_required
@admin_required
def enroll_student():
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            program_id = request.form.get('program_id')
            semester = request.form.get('semester')
            academic_year = request.form.get('academic_year')

            if not all([student_id, program_id, semester, academic_year]):
                flash('All fields are required.', 'error')
                return redirect(url_for('admin.enroll_student'))

            # Get student and program
            student = User.query.get_or_404(student_id)
            program = Program.query.get_or_404(program_id)

            if not student.is_student:
                flash('Selected user is not a student.', 'error')
                return redirect(url_for('admin.enroll_student'))

            # Get all active courses for the program in the given semester
            program_courses = Course.query.filter_by(
                program_id=program_id,
                semester=semester,
                status='active'
            ).all()

            # Check if student is already enrolled in any of these courses
            existing_enrollments = AcademicRecord.query.filter(
                AcademicRecord.student_id == student_id,
                AcademicRecord.course_id.in_([c.id for c in program_courses])
            ).all()

            if existing_enrollments:
                flash('Student is already enrolled in some courses for this program and semester.', 'warning')
                return redirect(url_for('admin.enroll_student'))

            # Create academic records for each course
            for course in program_courses:
                academic_record = AcademicRecord(
                    student_id=student_id,
                    course_id=course.id,
                    semester=semester,
                    academic_year=academic_year,
                    status='enrolled'
                )
                db.session.add(academic_record)

            db.session.commit()
            flash(f'Successfully enrolled student in {len(program_courses)} courses.', 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error enrolling student: {str(e)}', 'error')

    # Get all students and programs for the form
    students = User.query.filter_by(role=UserRole.STUDENT.value).all()
    programs = Program.query.all()
    current_year = datetime.utcnow().year
    academic_years = [f"{year}-{year+1}" for year in range(current_year-1, current_year+2)]
    semesters = ['Fall', 'Spring', 'Summer']

    return render_template('admin/enroll_student.html',
                         title='Enroll Student',
                         students=students,
                         programs=programs,
                         academic_years=academic_years,
                         semesters=semesters)

@admin.route('/admin/student_enrollments/<int:student_id>')
@login_required
@admin_required
def student_enrollments(student_id):
    student = User.query.get_or_404(student_id)
    if not student.is_student:
        flash('Selected user is not a student.', 'error')
        return redirect(url_for('admin.users'))

    enrollments = AcademicRecord.query.filter_by(student_id=student_id).all()
    return render_template('admin/student_enrollments.html',
                         title=f'Enrollments for {student.first_name} {student.last_name}',
                         student=student,
                         enrollments=enrollments)

@admin.route('/admin/unenroll_student/<int:student_id>/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def unenroll_student(student_id, course_id):
    academic_record = AcademicRecord.query.filter_by(
        student_id=student_id,
        course_id=course_id
    ).first_or_404()

    try:
        db.session.delete(academic_record)
        db.session.commit()
        flash('Successfully unenrolled student from the course.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error unenrolling student: {str(e)}', 'error')
    return redirect(url_for('admin.student_enrollments', student_id=student_id))

@admin.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    from sqlalchemy import func
    from datetime import timedelta
    from app.models.academic import Assignment, AssignmentSubmission
    from app.models.communication import Notification
    
    # User stats
    total_students = User.query.filter_by(role=UserRole.STUDENT.value).count()
    total_professors = User.query.filter_by(role=UserRole.PROFESSOR.value).count()
    total_admins = User.query.filter_by(role=UserRole.ADMIN.value).count()
    total_courses = Course.query.count()
    total_programs = Program.query.count()
    total_users = User.query.count()

    # Active users (last 30 days)
    last_30 = datetime.utcnow() - timedelta(days=30)
    active_users = User.query.filter(User.last_login != None, User.last_login >= last_30).count()

    # User registrations per month (last 12 months)
    months = []
    counts = []
    for i in range(11, -1, -1):
        month = (datetime.utcnow().replace(day=1) - timedelta(days=30*i))
        month_start = month.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        count = User.query.filter(User.created_at >= month_start, User.created_at < next_month).count()
        months.append(month_start.strftime('%b %Y'))
        counts.append(count)

    # User roles distribution
    roles_labels = ['Student', 'Professor', 'Admin']
    roles_counts = [total_students, total_professors, total_admins]

    # Students per program
    programs = Program.query.all()
    programs_labels = [p.name for p in programs]
    students_per_program = [User.query.filter_by(role=UserRole.STUDENT.value, program_id=p.id).count() for p in programs]

    # Grade distribution (all academic records)
    all_grades = [r.grade for r in AcademicRecord.query.filter(AcademicRecord.grade != None).all()]
    grade_bins = ['0-49', '50-59', '60-69', '70-79', '80-89', '90-100']
    grade_bin_counts = [0]*6
    for g in all_grades:
        if g < 50: grade_bin_counts[0] += 1
        elif g < 60: grade_bin_counts[1] += 1
        elif g < 70: grade_bin_counts[2] += 1
        elif g < 80: grade_bin_counts[3] += 1
        elif g < 90: grade_bin_counts[4] += 1
        else: grade_bin_counts[5] += 1

    # Top 5 courses by enrollment
    course_stats = []
    courses = Course.query.all()
    for course in courses:
        enrolled = AcademicRecord.query.filter_by(course_id=course.id).count()
        grades = [r.grade for r in AcademicRecord.query.filter_by(course_id=course.id).filter(AcademicRecord.grade != None).all()]
        avg_grade = sum(grades)/len(grades) if grades else None
        program_name = course.program.name if hasattr(course, 'program') and course.program else 'N/A'
        course_stats.append({
            'name': course.name,
            'program_name': program_name,
            'enrolled_students': enrolled,
            'average_grade': avg_grade
        })
    top_courses = sorted(course_stats, key=lambda c: c['enrolled_students'], reverse=True)[:5]

    return render_template('admin/analytics.html',
                         title='Analytics Dashboard',
                         total_students=total_students,
                         total_professors=total_professors,
                         total_admins=total_admins,
                         total_courses=total_courses,
                         total_programs=total_programs,
                         total_users=total_users,
                         active_users=active_users,
                         registrations_months=months,
                         registrations_counts=counts,
                         roles_labels=roles_labels,
                         roles_counts=roles_counts,
                         programs_labels=programs_labels,
                         students_per_program=students_per_program,
                         grade_bins=grade_bins,
                         grade_bin_counts=grade_bin_counts,
                         top_courses=top_courses)

@admin.route('/admin/system')
@login_required
@admin_required
def system_status():
    # Get system metrics
    metrics = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_courses': Course.query.count(),
        'active_courses': Course.query.filter_by(status='active').count(),
        'total_assignments': Assignment.query.count(),
        'pending_submissions': AssignmentSubmission.query.filter_by(status='submitted').count(),
        'total_notifications': Notification.query.count(),
        'unread_notifications': Notification.query.filter_by(read=False).count()
    }
    
    # Get recent activity
    recent_logins = User.query.order_by(User.last_login.desc()).limit(10).all()
    recent_submissions = AssignmentSubmission.query.order_by(
        AssignmentSubmission.submitted_at.desc()
    ).limit(10).all()
    
    return render_template('admin/system.html',
                         title='System Status',
                         metrics=metrics,
                         recent_logins=recent_logins,
                         recent_submissions=recent_submissions) 