# Import models here to make them available to Flask-Migrate
from app.models.user import User
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial, Program, Assignment, AssignmentSubmission
from app.models.communication import Message, Notification, Conversation, Discussion, DiscussionPost, Announcement
from app.models.admin import Admin 