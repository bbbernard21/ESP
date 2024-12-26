from app import db
from app.models.user import User, UserRole
from datetime import datetime

# Create professor user
professor = User(
    username='professor',
    email='professor@example.com',
    first_name='John',
    last_name='Doe',
    role=UserRole.PROFESSOR.value,
    created_at=datetime.utcnow(),
    is_active=True
)
professor.set_password('password123')

# Add to database
db.session.add(professor)
db.session.commit()

print('Professor user created successfully!') 