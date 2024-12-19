# Enhanced Student Portal - MVP

A comprehensive academic support system designed to enhance student engagement, progress tracking, and communication.

## MVP Features

1. Academic Records and Progress Tracking
   - Grade tracking
   - Academic goal setting
   - Progress feedback

2. Enhanced Communication Tools
   - Centralized messaging system
   - Real-time notification center

3. LMS Integration
   - Course materials access
   - Assignment submission

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
.\venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following variables:
```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///app.db
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## Project Structure

```
enhanced_student_portal/
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── templates/
│   └── static/
├── migrations/
├── tests/
├── .env
├── requirements.txt
└── run.py
``` 