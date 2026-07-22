"""Embedding Trainer - Offline fine-tuning of SentenceTransformer model using MultipleNegativesRankingLoss"""

import os
import json
import time
import torch
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, InputExample
from sentence_transformers.losses import MultipleNegativesRankingLoss

from app.models.model_embedding_training import EmbeddingTrainingSession
from app.services.topic.embedding_manager import EmbeddingManager
from app.services.topic.embedding_dataset import EmbeddingDatasetGenerator
from app.services.topic.embedding_evaluator import EmbeddingEvaluator

logger = logging.getLogger(__name__)


class EmbeddingTrainer:
    """Manages fine-tuning, versioning, evaluation, and automatic deployment of SentenceTransformer models"""

    def __init__(self, db: Session):
        self.db = db
        self.manager = EmbeddingManager()

    def _generate_next_version(self) -> str:
        """Query DB to determine the next version identifier (e.g., embedding_v1, embedding_v2)"""
        try:
            query = text("""
                SELECT version FROM embedding_training_sessions 
                ORDER BY id DESC LIMIT 1
            """)
            result = self.db.execute(query).first()
            if not result:
                return "embedding_v1"
            
            last_ver = result[0]
            if last_ver.startswith("embedding_v"):
                num = int(last_ver.replace("embedding_v", ""))
                return f"embedding_v{num + 1}"
            return f"embedding_v_{int(datetime.now().timestamp())}"
        except Exception as e:
            logger.warning(f"Error generating next version, using timestamp: {e}")
            return f"embedding_v_{int(datetime.now().timestamp())}"

    def run_fine_tuning(
        self,
        epochs: int = 2,
        batch_size: int = 64,
        learning_rate: float = 2e-5,
        warmup_ratio: float = 0.1,
        min_topic_size: int = 20,
        min_avg_prob: float = 0.85,
        max_pairs_per_topic: int = 200,
        min_doc_prob: float = 0.9,
        val_split: float = 0.1,
        force_train: bool = False
    ) -> Dict[str, Any]:
        """
        Run the offline embedding fine-tuning workflow:
        1. Query and filter high-quality training pairs from the DB.
        2. Create a training session in database.
        3. Train the model using MultipleNegativesRankingLoss.
        4. Evaluate the candidate model against the current model.
        5. Switch versions if metrics improve.
        """
        # Ensure rollback from any stale transactions
        try:
            self.db.rollback()
        except:
            pass

        # Step 1: Generate dataset
        dataset_generator = EmbeddingDatasetGenerator(self.db)
        session_id = dataset_generator.get_latest_completed_session()
        
        if not session_id and not force_train:
            return {
                "status": "skipped",
                "message": "No completed BERTopic sessions found in DB to generate training data"
            }

        # Check total new documents count if not forced (could be added based on trigger rule)
        # For manual/orchestrated run, we continue directly.

        train_examples, val_examples, num_docs_used = dataset_generator.generate_input_examples(
            min_topic_size=min_topic_size,
            min_avg_prob=min_avg_prob,
            max_pairs_per_topic=max_pairs_per_topic,
            min_doc_prob=min_doc_prob,
            val_split=val_split
        )

        if not train_examples:
            return {
                "status": "skipped",
                "message": f"Insufficient high-quality pairs generated. Adjust filters (topics size, probabilities)"
            }

        # Determine version and model paths
        version = self._generate_next_version()
        model_save_dir = self.manager.base_dir / version
        model_save_dir.mkdir(parents=True, exist_ok=True)
        
        # Create database session log
        started_at = datetime.now()
        db_session = EmbeddingTrainingSession(
            version=version,
            status="running",
            num_documents=num_docs_used,
            num_pairs=len(train_examples) + len(val_examples),
            epochs=epochs,
            started_at=started_at,
            model_path=str(model_save_dir)
        )
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)

        logger.info(f"Created embedding training session: {version} (ID: {db_session.id})")

        try:
            # Step 2: Initialize base model (load current active model as starting point)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Starting training on device: {device}")
            
            # Auto-fallback batch size if using CPU or low-memory environment
            actual_batch_size = batch_size
            if device == "cpu":
                logger.warning("CUDA is not available. Falling back to CPU training. Reducing batch size to 16 to avoid slowdowns.")
                actual_batch_size = min(16, batch_size)
            
            # Load base model from current active path
            current_model_path = self.manager.get_current_model_path()
            logger.info(f"Loading base model from: {current_model_path}")
            model = SentenceTransformer(current_model_path, device=device)

            # Step 3: Setup DataLoader and Loss
            train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=actual_batch_size)
            train_loss = MultipleNegativesRankingLoss(model)

            # Calculate warmup steps
            num_steps = len(train_dataloader) * epochs
            warmup_steps = int(num_steps * warmup_ratio)

            # Step 4: Fine-tune
            logger.info(f"Fine-tuning model: {version} - Steps: {num_steps}, Warmup Steps: {warmup_steps}")
            training_start_time = time.time()
            
            model.fit(
                train_objectives=[(train_dataloader, train_loss)],
                epochs=epochs,
                warmup_steps=warmup_steps,
                optimizer_params={"lr": learning_rate},
                show_progress_bar=False
            )
            
            training_duration = time.time() - training_start_time
            logger.info(f"Fine-tuning finished in {training_duration:.1f} seconds")

            # Save the candidate model
            model.save(str(model_save_dir))
            logger.info(f"Candidate model saved to: {model_save_dir}")

            # Step 5: Evaluation
            logger.info("Evaluating candidate model against current deployed model...")
            
            # Prepare validation pairs for evaluator: List of (doc_a, doc_b, topic_id)
            # Reconstruct list of validation tuples from generators or use subset
            # Let's map val_examples back to tuples (we didn't store topic labels in val_examples, 
            # so let's parse raw validation pairs directly)
            # To do that, we get validation pairs from dataset generator
            latest_session_id = dataset_generator.get_latest_completed_session()
            topics = dataset_generator.get_high_quality_topics(
                session_id=latest_session_id,
                min_topic_size=min_topic_size,
                min_avg_prob=min_avg_prob
            )
            raw_pairs = dataset_generator.build_positive_pairs(
                topics=topics,
                session_id=latest_session_id,
                max_pairs_per_topic=max_pairs_per_topic,
                min_doc_prob=min_doc_prob
            )
            
            # Re-seed and split to match val_examples exactly
            import random
            random.seed(42)
            random.shuffle(raw_pairs)
            split_idx = int(len(raw_pairs) * (1 - val_split))
            val_pairs = raw_pairs[split_idx:]

            evaluator = EmbeddingEvaluator(val_pairs)
            
            # Evaluate Current Model
            logger.info("Evaluating currently active model...")
            current_model = self.manager.get_current_model(device=device)
            current_metrics = evaluator.evaluate(current_model)
            
            # Evaluate Candidate Model
            logger.info("Evaluating candidate model...")
            candidate_metrics = evaluator.evaluate(model)

            # Compare metrics
            is_better, reason = EmbeddingEvaluator.is_candidate_better(current_metrics, candidate_metrics)
            
            # Save metadata inside candidate folder
            metadata = {
                "version": version,
                "base_model": current_model_path,
                "trained_at": datetime.now().isoformat(),
                "num_documents": num_docs_used,
                "num_pairs": len(train_examples) + len(val_examples),
                "duration_seconds": training_duration,
                "epochs": epochs,
                "batch_size": actual_batch_size,
                "learning_rate": learning_rate,
                "evaluation": {
                    "current_metrics": current_metrics,
                    "candidate_metrics": candidate_metrics,
                    "deployed": is_better,
                    "deployment_reason": reason
                }
            }
            
            with open(model_save_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Switch deployed version if candidate is better
            status = "completed"
            if is_better:
                logger.info(f"Candidate model IS better: {reason}")
                deployed = self.manager.set_active_version(
                    version=version,
                    model_path=str(model_save_dir),
                    notes=f"Auto-deployed fine-tuned model: {reason}"
                )
                if deployed:
                    status = "deployed"
            else:
                logger.info(f"Candidate model is NOT deployed: {reason}")
                status = "evaluated"

            # Update DB session
            db_session.status = status
            db_session.finished_at = datetime.now()
            db_session.metrics = candidate_metrics
            self.db.commit()
            
            logger.info(f"Embedding training session completed successfully. Status: {status}")
            
            return {
                "status": "success",
                "version": version,
                "db_session_id": db_session.id,
                "deployed": is_better,
                "reason": reason,
                "metrics": candidate_metrics
            }

        except Exception as e:
            logger.error(f"Embedding fine-tuning failed: {e}", exc_info=True)
            self.db.rollback()
            try:
                db_session.status = "failed"
                db_session.finished_at = datetime.now()
                db_session.error_message = str(e)
                self.db.commit()
            except Exception as dbe:
                logger.error(f"Failed to update failed status in database: {dbe}")
                
            return {
                "status": "failed",
                "version": version,
                "error": str(e)
            }
