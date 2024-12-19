from app import create_app, db
from app.models.user import User
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial
from app.models.communication import Message, Notification, Discussion, DiscussionPost

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Course': Course,
        'AcademicRecord': AcademicRecord,
        'AcademicGoal': AcademicGoal,
        'CourseMaterial': CourseMaterial,
        'Message': Message,
        'Notification': Notification,
        'Discussion': Discussion,
        'DiscussionPost': DiscussionPost
    }

if __name__ == '__main__':
    app.run(debug=True) 