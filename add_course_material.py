from app import create_app, db
from app.models.academic import Course, CourseMaterial
import os
from datetime import datetime

def add_course_material():
    app = create_app()
    with app.app_context():
        # Get the Data Structures course
        course = Course.query.filter_by(name='Data Structures').first()
        if not course:
            print("Data Structures course not found")
            return

        # Create the material entry
        material = CourseMaterial(
            course_id=course.id,
            title="Learning Material",
            description="PowerPoint presentation for learning materials",
            file_path="course_materials/learning_material.pptx",
            material_type="presentation",
            created_at=datetime.utcnow()
        )

        try:
            db.session.add(material)
            db.session.commit()
            print("Course material added successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding course material: {str(e)}")

if __name__ == '__main__':
    add_course_material() 