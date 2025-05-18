# early_warning.py
# Utility functions for predictive analytics & early warning system
from app.models.user import User
from app.models.academic import AcademicRecord, Assignment, AssignmentSubmission, Exam, ExamGrade
from app.models.communication import Notification
from app import db
from datetime import datetime, timedelta

def calculate_risk_factors(student_id):
    """
    Calculate risk score and reasons for a student based on academic performance and engagement.
    Returns: (risk_score: float, risk_reasons: list of str)
    """
    risk_score = 0
    risk_reasons = []
    student = User.query.get(student_id)
    if not student or not student.is_student:
        return 0, []

    # 1. Low grades (average < 60%)
    records = AcademicRecord.query.filter_by(student_id=student_id).all()
    if records:
        grades = [r.grade for r in records if r.grade is not None]
        if grades:
            avg_grade = sum(grades) / len(grades)
            if avg_grade < 60:
                risk_score += 0.5
                risk_reasons.append(f"Low average grade: {avg_grade:.1f}%")

    # 2. Missing assignments
    assignments = Assignment.query.join(AcademicRecord, Assignment.course_id == AcademicRecord.course_id)
    assignments = assignments.filter(AcademicRecord.student_id == student_id).all()
    for assignment in assignments:
        submission = AssignmentSubmission.query.filter_by(student_id=student_id, assignment_id=assignment.id).first()
        if not submission or submission.status != 'graded':
            if assignment.due_date < datetime.utcnow():
                risk_score += 0.2
                risk_reasons.append(f"Missing assignment: {assignment.title}")

    # 3. Missed or failed exams
    exams = Exam.query.join(AcademicRecord, Exam.course_id == AcademicRecord.course_id)
    exams = exams.filter(AcademicRecord.student_id == student_id).all()
    for exam in exams:
        grade = ExamGrade.query.filter_by(student_id=student_id, exam_id=exam.id).first()
        if not grade and exam.exam_date < datetime.utcnow():
            risk_score += 0.2
            risk_reasons.append(f"Missed exam: {exam.title}")
        elif grade and grade.grade < 60:
            risk_score += 0.2
            risk_reasons.append(f"Low exam grade: {exam.title} ({grade.grade}%)")

    # 4. Engagement (not implemented: placeholder for future)
    # Add more factors as needed

    return min(risk_score, 1.0), risk_reasons

def trigger_early_warning(student_id):
    """
    Analyze student and create notification if at-risk.
    """
    risk_score, reasons = calculate_risk_factors(student_id)
    if risk_score >= 0.5:
        # Create notification if not already exists for today
        today = datetime.utcnow().date()
        existing = Notification.query.filter_by(user_id=student_id, category='early_warning').filter(Notification.created_at >= today).first()
        if not existing:
            body = 'You have been flagged as at-risk for the following reasons: ' + '; '.join(reasons)
            notif = Notification(user_id=student_id, title='Academic Early Warning', body=body, category='early_warning')
            db.session.add(notif)
            db.session.commit()
        return True, reasons
    return False, reasons

def check_all_students_and_alert():
    """
    Run early warning check for all students (to be called by admin/professor or via scheduled task).
    """
    students = User.query.filter_by(role='STUDENT').all()
    results = []
    for student in students:
        flagged, reasons = trigger_early_warning(student.id)
        if flagged:
            results.append({'student_id': student.id, 'reasons': reasons})
    return results
