# Import models here to make them available to Flask-Migrate
from app.models.user import User
from app.models.academic import Course, AcademicRecord, AcademicGoal, CourseMaterial
from app.models.communication import Message, Notification, Discussion, DiscussionPost 