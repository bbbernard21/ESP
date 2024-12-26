from datetime import datetime, timedelta
from app import db
from app.models.academic import Course, AcademicRecord, Assignment, AssignmentSubmission, Exam, ExamGrade
from app.models.communication import Notification
from sqlalchemy import func

def calculate_course_grades():
    """Calculate final grades for all enrolled students in active courses."""
    courses = Course.query.filter_by(status='active').all()
    
    for course in courses:
        academic_records = AcademicRecord.query.filter_by(
            course_id=course.id,
            status='enrolled'
        ).all()
        
        for record in academic_records:
            # Calculate assignment grade
            assignment_grades = AssignmentSubmission.query.join(Assignment).filter(
                Assignment.course_id == course.id,
                AssignmentSubmission.student_id == record.student_id,
                AssignmentSubmission.status == 'graded'
            ).with_entities(
                func.avg(AssignmentSubmission.grade).label('avg_grade')
            ).first()
            
            assignment_grade = assignment_grades.avg_grade or 0
            
            # Calculate exam grades
            midterm_grade = ExamGrade.query.join(Exam).filter(
                Exam.course_id == course.id,
                ExamGrade.student_id == record.student_id,
                Exam.exam_type == 'midterm'
            ).with_entities(ExamGrade.grade).first()
            
            final_grade = ExamGrade.query.join(Exam).filter(
                Exam.course_id == course.id,
                ExamGrade.student_id == record.student_id,
                Exam.exam_type == 'final'
            ).with_entities(ExamGrade.grade).first()
            
            # Calculate weighted final grade
            final_course_grade = (
                (assignment_grade * course.assignments_weight / 100) +
                ((midterm_grade.grade if midterm_grade else 0) * course.midterm_weight / 100) +
                ((final_grade.grade if final_grade else 0) * course.final_weight / 100)
            )
            
            # Update academic record
            record.grade = final_course_grade
            db.session.add(record)
    
    db.session.commit()

def check_deadlines():
    """Check for upcoming deadlines and send notifications."""
    # Check assignment deadlines
    upcoming_assignments = Assignment.query.filter(
        Assignment.due_date > datetime.utcnow(),
        Assignment.due_date <= datetime.utcnow() + timedelta(days=7)
    ).all()
    
    for assignment in upcoming_assignments:
        # Get enrolled students who haven't submitted
        enrolled_students = AcademicRecord.query.filter_by(
            course_id=assignment.course_id,
            status='enrolled'
        ).all()
        
        for record in enrolled_students:
            submission = AssignmentSubmission.query.filter_by(
                assignment_id=assignment.id,
                student_id=record.student_id
            ).first()
            
            if not submission:
                # Create notification
                notification = Notification(
                    user_id=record.student_id,
                    title='Assignment Due Soon',
                    body=f'Assignment "{assignment.title}" for {assignment.course.name} is due on {assignment.due_date.strftime("%Y-%m-%d")}',
                    category='academic',
                    priority='high'
                )
                db.session.add(notification)
    
    # Check exam dates
    upcoming_exams = Exam.query.filter(
        Exam.exam_date > datetime.utcnow(),
        Exam.exam_date <= datetime.utcnow() + timedelta(days=14)
    ).all()
    
    for exam in upcoming_exams:
        enrolled_students = AcademicRecord.query.filter_by(
            course_id=exam.course_id,
            status='enrolled'
        ).all()
        
        for record in enrolled_students:
            notification = Notification(
                user_id=record.student_id,
                title='Upcoming Exam',
                body=f'{exam.title} for {exam.course.name} is scheduled for {exam.exam_date.strftime("%Y-%m-%d")}',
                category='academic',
                priority='high'
            )
            db.session.add(notification)
    
    db.session.commit()

def generate_analytics():
    """Generate analytics for courses and students."""
    courses = Course.query.filter_by(status='active').all()
    
    for course in courses:
        # Calculate course statistics
        records = AcademicRecord.query.filter_by(course_id=course.id).all()
        grades = [r.grade for r in records if r.grade is not None]
        
        if grades:
            course.average_grade = sum(grades) / len(grades)
            course.highest_grade = max(grades)
            course.lowest_grade = min(grades)
            course.passing_rate = len([g for g in grades if g >= 60]) / len(grades) * 100
            
            db.session.add(course)
    
    db.session.commit() 