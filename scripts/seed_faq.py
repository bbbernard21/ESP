from app import create_app, db
from app.models.faq import FAQ

app = create_app()

import openai
import os

def get_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    # For openai>=1.0, the embedding is at response.data[0].embedding
    return response.data[0].embedding

with app.app_context():
    faqs = [
        FAQ(question="How do I submit an assignment?", answer="Go to your course page, click 'Assignments', and upload your file."),
        FAQ(question="How can I view my grades?", answer="Visit your dashboard and select 'Grades' from the menu."),
        FAQ(question="Who do I contact for technical support?", answer="Use the Help section or contact support@example.com"),
        FAQ(question="Where can I find course materials?", answer="Course materials are available on each course's page under 'Materials'."),
        FAQ(question="How do I join a group discussion?", answer="Go to the 'Discussions' tab in your course page and join any active thread.")
    ]
    for faq in faqs:
        faq.embedding = get_embedding(faq.question)
        existing = FAQ.query.filter_by(question=faq.question).first()
        if existing:
            existing.answer = faq.answer
            existing.embedding = faq.embedding
        else:
            db.session.add(faq)
    db.session.commit()
    print("Sample FAQs with embeddings seeded (updated in-place if already present).")
