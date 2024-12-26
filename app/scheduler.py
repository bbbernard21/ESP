from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks import calculate_course_grades, check_deadlines, generate_analytics

def init_scheduler():
    """Initialize the scheduler with automated tasks."""
    scheduler = BackgroundScheduler()
    
    # Calculate grades daily at midnight
    scheduler.add_job(
        calculate_course_grades,
        CronTrigger(hour=0, minute=0),
        id='calculate_grades',
        name='Calculate course grades'
    )
    
    # Check deadlines every 6 hours
    scheduler.add_job(
        check_deadlines,
        CronTrigger(hour='*/6'),
        id='check_deadlines',
        name='Check assignment and exam deadlines'
    )
    
    # Generate analytics every day at 1 AM
    scheduler.add_job(
        generate_analytics,
        CronTrigger(hour=1, minute=0),
        id='generate_analytics',
        name='Generate course and student analytics'
    )
    
    scheduler.start() 