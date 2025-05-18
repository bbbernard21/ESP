# ESP - Enhanced Student Portal (LMS)

A comprehensive Learning Management System (LMS) built with Flask, designed to enhance student engagement, progress tracking, analytics, and communication for universities and educational institutions.

---

## Features

- **Role-Based Access:** Separate dashboards and permissions for Students, Professors, and Admins.
- **RAG Chatbot:** AI-powered chatbot for student support, integrated in the student dashboard.
- **Student Analytics:** Track grades, attendance, participation, and set academic goals.
- **Professor Analytics:** View course statistics, student progress, engagement metrics, and early warnings.
- **Admin Panel:** Manage users, courses, programs, and system settings.
- **Communication Tools:** Messaging, notifications, discussion forums, and announcements.
- **Assignments & Exams:** Submission, grading, quizzes, and feedback.
- **Course Materials:** Upload/download resources and manage content.
- **Real-Time Features:** Notifications and chat with JavaScript enhancements.
- **Scheduler:** Automated analytics generation and scheduled tasks.
- **Migration Scripts:** Versioned database migrations for evolving schema.

---

## Tech Stack

- **Backend:** Python, Flask, Flask-Login, APScheduler
- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **Database:** SQLite (default, configurable)
- **Other:** OpenAI API (for chatbot), Jinja2 templates, Alembic migrations

---

## Getting Started

1. **Clone the repository:**
   ```sh
   git clone https://github.com/bbbernard21/ESP.git
   cd ESP
   ```

2. **Set up a virtual environment:**
   ```sh
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in the required values (see `.env` for reference).

5. **Initialize the database:**
   ```sh
   flask db upgrade
   ```

6. **(Optional) Generate test data:**
   ```sh
   python app/generate_test_data.py
   ```

7. **Run the application:**
   ```sh
   flask run
   ```

---

## Project Structure

```
ESP/
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── generate_test_data.py
│   ├── models/
│   ├── routes/
│   ├── scheduler.py
│   ├── static/
│   ├── tasks.py
│   ├── templates/
│   ├── test_data.py
│   └── utils/
├── migrations/
├── requirements.txt
├── run.py
├── scripts/
├── .env
└── README.md
```

---
