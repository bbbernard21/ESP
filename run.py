from app import create_app, db
from app.models.user import User
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial, Program, Assignment, AssignmentSubmission
from app.models.communication import Message, Notification, Conversation, Discussion, DiscussionPost, Announcement
from app.models.admin import Admin

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Course': Course,
        'Program': Program,
        'AcademicRecord': AcademicRecord,
        'AcademicGoal': AcademicGoal,
        'CourseMaterial': CourseMaterial,
        'Assignment': Assignment,
        'AssignmentSubmission': AssignmentSubmission,
        'Message': Message,
        'Notification': Notification,
        'Conversation': Conversation,
        'Discussion': Discussion,
        'DiscussionPost': DiscussionPost,
        'Admin': Admin,
        'Announcement': Announcement
    }

if __name__ == '__main__':
    app.run(debug=True) 