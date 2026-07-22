import sys
from app.core.database import SessionLocal
from app.models.model_bertopic_discovered import TopicTrainingSession
from sqlalchemy import desc

db = SessionLocal()
try:
    sessions = db.query(TopicTrainingSession).order_by(desc(TopicTrainingSession.started_at)).limit(10).all()
    print("SESSION_ID | STATUS | DOCS | TOPICS | DURATION (sec) | STARTED_AT")
    print("-" * 80)
    for s in sessions:
        print(f"{s.session_id} | {s.status} | {s.num_documents} | {s.num_topics_found} | {s.training_duration_seconds} | {s.started_at}")
finally:
    db.close()
