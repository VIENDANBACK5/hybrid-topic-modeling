import os
import shutil
import json
from pathlib import Path
from app.core.database import SessionLocal
from app.models.model_article import Article
from app.models.model_bertopic_discovered import TopicTrainingSession, BertopicDiscoveredTopic, ArticleBertopicTopic
from app.models.model_embedding_training import EmbeddingTrainingSession

print("Starting clean up of test resources...")

# 1. Reset database records
db = SessionLocal()
try:
    # Delete test article bertopic topics mapping
    db.query(ArticleBertopicTopic).filter(ArticleBertopicTopic.training_session_id.like("session_test_%")).delete(synchronize_session=False)
    # Delete test bertopic discovered topics
    db.query(BertopicDiscoveredTopic).filter(BertopicDiscoveredTopic.training_session_id.like("session_test_%")).delete(synchronize_session=False)
    # Delete test topic training sessions
    db.query(TopicTrainingSession).filter(TopicTrainingSession.session_id.like("session_test_%")).delete(synchronize_session=False)
    # Delete test articles
    db.query(Article).filter(Article.id > 1000).delete(synchronize_session=False)
    # Delete test embedding training sessions
    db.query(EmbeddingTrainingSession).filter(EmbeddingTrainingSession.version.like("embedding_v%")).delete(synchronize_session=False)
    db.commit()
    print(" Successfully deleted test database records.")
except Exception as e:
    db.rollback()
    print(f" Error resetting database records: {e}")
finally:
    db.close()

# 2. Reset active_version.json to default
config_path = Path("data/models/embedding/active_version.json")
if config_path.exists():
    default_config = {
        "active_version": "default",
        "model_path": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "deployed_at": None,
        "notes": "Reset to default model after verification tests"
    }
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print(" Successfully reset active_version.json to default.")
    except Exception as e:
        print(f" Error resetting active_version.json: {e}")

# 3. Delete generated model folders under data/models/embedding
embedding_dir = Path("data/models/embedding")
if embedding_dir.exists():
    for folder in embedding_dir.iterdir():
        if folder.is_dir() and (folder.name.startswith("embedding_v") or folder.name.startswith("version_")):
            try:
                shutil.rmtree(folder)
                print(f" Deleted test model directory: {folder}")
            except Exception as e:
                print(f" Error deleting folder {folder}: {e}")

# 4. Remove scratch files
for file_path in ["scratch_session_info.py"]:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f" Removed scratch file: {file_path}")

print("Clean up completed.")
