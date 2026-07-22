"""Embedding Evaluator - Compare candidate fine-tuned models against current production model"""

import numpy as np
import logging
from typing import List, Dict, Tuple, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class EmbeddingEvaluator:
    """Computes production-ready evaluation metrics for embedding models on validation sets"""

    def __init__(self, validation_pairs: List[Tuple[str, str, int]]):
        """
        Args:
            validation_pairs: List of Tuple (doc_a, doc_b, topic_id)
        """
        self.validation_pairs = validation_pairs

    def evaluate(self, model: SentenceTransformer) -> Dict[str, float]:
        """
        Evaluate a model on the validation set.
        Returns:
            Dict containing Silhouette Score, Average Similarity, and Retrieval Accuracy
        """
        if not self.validation_pairs:
            logger.warning("Empty validation pairs. Cannot run evaluation.")
            return {
                "silhouette_score": 0.0,
                "avg_cosine_similarity": 0.0,
                "retrieval_mrr": 0.0,
                "retrieval_hit_rate_at_3": 0.0
            }

        # Extract documents and labels
        doc_as = [p[0] for p in self.validation_pairs]
        doc_bs = [p[1] for p in self.validation_pairs]
        labels = [p[2] for p in self.validation_pairs]
        
        # 1. Compute Embeddings
        logger.info(f"Encoding {len(doc_as) * 2} validation documents...")
        embeddings_a = model.encode(doc_as, show_progress_bar=False, convert_to_numpy=True)
        embeddings_b = model.encode(doc_bs, show_progress_bar=False, convert_to_numpy=True)
        
        # 2. Compute Average Cosine Similarity on positive pairs
        # Cosine similarity = dot_product(a, b) / (norm(a) * norm(b))
        # Normalize first to make dot product equivalent to cosine similarity
        norm_a = embeddings_a / np.linalg.norm(embeddings_a, axis=1, keepdims=True)
        norm_b = embeddings_b / np.linalg.norm(embeddings_b, axis=1, keepdims=True)
        
        similarities = np.sum(norm_a * norm_b, axis=1)
        avg_similarity = float(np.mean(similarities))
        
        # 3. Compute Silhouette Score
        # We merge doc_as and doc_bs and use topic_labels
        all_docs_embeddings = np.vstack([norm_a, norm_b])
        all_labels = labels + labels
        
        sil_score = 0.0
        unique_labels = len(set(all_labels))
        if unique_labels > 1 and len(all_labels) > unique_labels:
            try:
                # To prevent performance bottleneck on large sets, cap the sample size
                sample_cap = min(1000, len(all_labels))
                if sample_cap < len(all_labels):
                    indices = np.random.choice(len(all_labels), sample_cap, replace=False)
                    sampled_embeddings = all_docs_embeddings[indices]
                    sampled_labels = [all_labels[idx] for idx in indices]
                    sil_score = float(silhouette_score(sampled_embeddings, sampled_labels, metric='cosine'))
                else:
                    sil_score = float(silhouette_score(all_docs_embeddings, all_labels, metric='cosine'))
            except Exception as e:
                logger.warning(f"Failed to compute Silhouette score: {e}")
                sil_score = 0.0
        else:
            logger.warning("Not enough clusters/samples to compute Silhouette score.")

        # 4. Compute Retrieval Accuracy (MRR & Hit Rate @ 3)
        # Construct retrieval task: doc_a is query, doc_b is targets
        # Search query in target pool
        # Cosine similarity matrix: queries (A) x targets (B)
        similarity_matrix = np.dot(norm_a, norm_b.T)  # Shape: (N, N)
        
        mrr = 0.0
        hits_at_3 = 0.0
        n = len(doc_as)
        
        for i in range(n):
            # Rank similarity of query i to all target documents
            sims = similarity_matrix[i]
            # Argsort sorts ascending, reverse to get descending ranks
            ranks = np.argsort(sims)[::-1]
            
            # Find rank of the correct target (index i)
            correct_rank_idx = np.where(ranks == i)[0][0]  # 0-indexed rank
            rank = correct_rank_idx + 1  # 1-indexed rank
            
            # Reciprocal Rank
            mrr += 1.0 / rank
            
            # Hit rate @ 3
            if rank <= 3:
                hits_at_3 += 1.0
                
        retrieval_mrr = float(mrr / n)
        retrieval_hit_rate_at_3 = float(hits_at_3 / n)

        metrics = {
            "silhouette_score": sil_score,
            "avg_cosine_similarity": avg_similarity,
            "retrieval_mrr": retrieval_mrr,
            "retrieval_hit_rate_at_3": retrieval_hit_rate_at_3
        }
        
        logger.info(f"Evaluation completed. Metrics: {metrics}")
        return metrics

    @staticmethod
    def is_candidate_better(current_metrics: Dict[str, float], candidate_metrics: Dict[str, float]) -> Tuple[bool, str]:
        """
        Compare candidate model metrics with current model metrics.
        Returns:
            (is_better, reason)
        """
        # Comparison logic:
        # A candidate is better if it shows improvement across retrieval accuracy and silhouette score,
        # or at least a significant improvement in retrieval without degrading silhouette drastically.
        
        # Base thresholds/weights
        cand_mrr = candidate_metrics.get("retrieval_mrr", 0.0)
        curr_mrr = current_metrics.get("retrieval_mrr", 0.0)
        
        cand_sil = candidate_metrics.get("silhouette_score", 0.0)
        curr_sil = current_metrics.get("silhouette_score", 0.0)
        
        cand_sim = candidate_metrics.get("avg_cosine_similarity", 0.0)
        curr_sim = current_metrics.get("avg_cosine_similarity", 0.0)
        
        logger.info(f"Comparing current MRR: {curr_mrr:.4f} vs Candidate MRR: {cand_mrr:.4f}")
        logger.info(f"Comparing current Silhouette: {curr_sil:.4f} vs Candidate Silhouette: {cand_sil:.4f}")
        
        # Avoid deploying if retrieval accuracy degrades
        if cand_mrr < curr_mrr - 0.01:
            return False, f"Retrieval accuracy degraded significantly (Current MRR: {curr_mrr:.4f}, Candidate MRR: {cand_mrr:.4f})"
            
        # Avoid deploying if silhouette score drops drastically (more than 0.05)
        if cand_sil < curr_sil - 0.05:
            return False, f"Cluster separation degraded significantly (Current Silhouette: {curr_sil:.4f}, Candidate Silhouette: {cand_sil:.4f})"
            
        # Accept if MRR is better, or if similarity is significantly higher without degradation elsewhere
        if cand_mrr > curr_mrr + 0.005:
            return True, f"Retrieval MRR improved from {curr_mrr:.4f} to {cand_mrr:.4f}"
            
        if cand_sil > curr_sil + 0.01:
            return True, f"Clustering Silhouette score improved from {curr_sil:.4f} to {cand_sil:.4f}"
            
        if cand_sim > curr_sim + 0.02 and cand_mrr >= curr_mrr:
            return True, f"Positive pair similarity improved from {curr_sim:.4f} to {cand_sim:.4f}"

        return False, "Candidate metrics show no significant improvement over current production model"
