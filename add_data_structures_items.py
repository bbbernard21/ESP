from app import create_app, db
from app.models.academic import Course, Assignment, Exam
from datetime import datetime, timedelta

def add_data_structures_items():
    app = create_app()
    with app.app_context():
        # Get the Data Structures course
        course = Course.query.filter_by(code='CS102').first()
        if not course:
            print("Data Structures course not found")
            return

        # Create assignments
        assignments_data = [
            {
                'course_id': course.id,
                'title': 'Array Implementation',
                'description': 'Implement basic array operations and analyze their time complexity',
                'due_date': datetime.utcnow() + timedelta(days=7),
                'total_points': 100,
                'weight': 10
            },
            {
                'course_id': course.id,
                'title': 'Linked List Operations',
                'description': 'Implement singly and doubly linked lists with various operations',
                'due_date': datetime.utcnow() + timedelta(days=14),
                'total_points': 100,
                'weight': 10
            },
            {
                'course_id': course.id,
                'title': 'Stack and Queue Implementation',
                'description': 'Implement stack and queue data structures using arrays and linked lists',
                'due_date': datetime.utcnow() + timedelta(days=21),
                'total_points': 100,
                'weight': 10
            },
            {
                'course_id': course.id,
                'title': 'Binary Search Tree',
                'description': 'Implement a binary search tree with insertion, deletion, and traversal operations',
                'due_date': datetime.utcnow() + timedelta(days=28),
                'total_points': 100,
                'weight': 10
            }
        ]

        # Create exams
        exams_data = [
            {
                'course_id': course.id,
                'title': 'Midterm Exam',
                'description': 'Covers arrays, linked lists, stacks, and queues',
                'exam_date': datetime.utcnow() + timedelta(days=30),
                'duration': 120,  # minutes
                'total_points': 100,
                'weight': 25.0
            },
            {
                'course_id': course.id,
                'title': 'Final Exam',
                'description': 'Comprehensive exam covering all data structures and algorithms',
                'exam_date': datetime.utcnow() + timedelta(days=90),
                'duration': 180,  # minutes
                'total_points': 100,
                'weight': 35.0
            }
        ]

        # Add assignments to database
        for assignment_data in assignments_data:
            assignment = Assignment(**assignment_data)
            db.session.add(assignment)

        # Add exams to database
        for exam_data in exams_data:
            exam = Exam(**exam_data)
            db.session.add(exam)

        # Commit changes
        db.session.commit()
        print("Successfully added assignments and exams to Data Structures course")

if __name__ == '__main__':
    add_data_structures_items() 