from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models.faq import FAQ
import openai
import os

chatbot_bp = Blueprint('chatbot', __name__)

OPENAI_MODEL = "gpt-4.1-2025-04-14"

# Create OpenAI client (new API)
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@chatbot_bp.route('/api/chatbot/ask', methods=['POST'])
@login_required
def ask_chatbot():
    # Restrict access to students only
    from flask_login import current_user
    if not getattr(current_user, 'is_student', False):
        return jsonify({'error': 'Access denied: Only students can use the chatbot.'}), 403

    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided.'}), 400

    from app.models.academic import Course, AcademicRecord, Assignment, AssignmentSubmission, CourseMaterial
    from app.models.faq import FAQ
    from flask_login import current_user

    # --- User Info ---
    user_info = f"Name: {current_user.first_name} {current_user.last_name}\nEmail: {current_user.email}"

    # --- Courses & Grades ---
    course_lines = []
    material_lines = []
    assignment_lines = []
    academic_records = current_user.academic_records.filter_by(status='enrolled').all()
    for record in academic_records:
        course = record.course
        if course is None:
            continue  # Defensive: skip if course is missing
        grade = record.grade if record.grade is not None else 'N/A'
        course_lines.append(f"- {course.code}: {course.name} (Grade: {grade})")
        # Materials for this course
        for mat in course.materials:
            material_lines.append(f"- [{course.code}] {mat.title}: {mat.file_path or 'No file'}")
        # Assignments for this course
        for assignment in course.assignments:
            submission = next((s for s in assignment.submissions if s.student_id == current_user.id), None)
            status = 'Submitted' if submission else 'Not Submitted'
            grade = submission.grade if submission and submission.grade is not None else 'N/A'
            assignment_lines.append(f"- [{course.code}] {assignment.title}: {status}, Grade: {grade}")

    # --- Announcements ---
    from app.models.communication import Announcement
    announcement_lines = []
    for record in academic_records:
        course = record.course
        if course is None:
            continue
        for ann in getattr(course, 'announcements', []):
            announcement_lines.append(f"- [{course.code}] {ann.title}: {ann.content}")

    # --- Exams ---
    exam_lines = []
    for record in academic_records:
        course = record.course
        if course is None:
            continue
        for exam in getattr(course, 'exams', []):
            grade_obj = exam.get_grade(current_user.id) if hasattr(exam, 'get_grade') else None
            grade = grade_obj.grade if grade_obj and hasattr(grade_obj, 'grade') else 'N/A'
            exam_lines.append(f"- [{course.code}] {exam.title}: {exam.exam_date.strftime('%Y-%m-%d')} | Grade: {grade}")

    # --- Quizzes ---
    quiz_lines = []
    for record in academic_records:
        course = record.course
        if course is None:
            continue
        for quiz in getattr(course, 'quizzes', []):
            submission = quiz.get_submission(current_user.id) if hasattr(quiz, 'get_submission') else None
            score = submission.score if submission and hasattr(submission, 'score') else 'N/A'
            quiz_lines.append(f"- [{course.code}] {quiz.title}: Score: {score}")

    # --- Exams ---
    exam_lines = []
    for record in academic_records:
        course = record.course
        for exam in getattr(course, 'exams', []):
            grade_obj = exam.get_grade(current_user.id) if hasattr(exam, 'get_grade') else None
            grade = grade_obj.grade if grade_obj and hasattr(grade_obj, 'grade') else 'N/A'
            exam_lines.append(f"- [{course.code}] {exam.title}: {exam.exam_date.strftime('%Y-%m-%d')} | Grade: {grade}")

    # --- Quizzes ---
    quiz_lines = []
    for record in academic_records:
        course = record.course
        for quiz in getattr(course, 'quizzes', []):
            submission = quiz.get_submission(current_user.id) if hasattr(quiz, 'get_submission') else None
            score = submission.score if submission and hasattr(submission, 'score') else 'N/A'
            quiz_lines.append(f"- [{course.code}] {quiz.title}: Score: {score}")

    # --- FAQs (Semantic Search) ---
    import numpy as np
    import openai
    def get_embedding(text):
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding

    question_emb = get_embedding(question)
    all_faqs = FAQ.query.all()
    faq_scores = []
    for faq in all_faqs:
        if faq.embedding:
            score = 1 - np.dot(question_emb, faq.embedding) / (np.linalg.norm(question_emb) * np.linalg.norm(faq.embedding))
            faq_scores.append((faq, score))
    faq_scores.sort(key=lambda x: x[1])  # Lower distance = more similar
    top_faqs = [faq for faq, _ in faq_scores[:3]]
    faq_lines = [f"Q: {f.question}\nA: {f.answer}" for f in top_faqs]
    
    # --- Prompt Construction ---
    prompt = f"""
User Info:\n{user_info}

Courses:\n{chr(10).join(course_lines) if course_lines else 'No enrolled courses.'}

Assignments:\n{chr(10).join(assignment_lines) if assignment_lines else 'No assignments found.'}

Materials:\n{chr(10).join(material_lines) if material_lines else 'No materials found.'}

Announcements:\n{chr(10).join(announcement_lines) if announcement_lines else 'No announcements.'}

Exams:\n{chr(10).join(exam_lines) if exam_lines else 'No exams.'}

Quizzes:\n{chr(10).join(quiz_lines) if quiz_lines else 'No quizzes.'}

FAQs:\n{chr(10).join(faq_lines) if faq_lines else 'No relevant FAQs found.'}

User Question: {question}\nAnswer:
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an academic assistant chatbot. Answer student questions using the provided context. If unsure, say you don't know."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=512
        )
        answer = response.choices[0].message.content.strip()
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
