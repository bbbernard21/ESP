from app import db

class FAQ(db.Model):
    __tablename__ = 'faqs'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.PickleType)  # Stores the embedding vector as a Python list

    def __repr__(self):
        return f'<FAQ {self.id}: {self.question[:20]}>'
