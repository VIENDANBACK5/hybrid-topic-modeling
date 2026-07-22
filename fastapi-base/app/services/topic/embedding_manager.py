"""Embedding Manager - Manage SentenceTransformer model versions, switching, and fallback"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_BASE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIR = Path("data/models/embedding")
CONFIG_FILE = EMBEDDING_DIR / "active_version.json"


class EmbeddingManager:
    """Manages active fine-tuned embedding models, version switching, and database configurations"""

    def __init__(self, base_dir: Path = EMBEDDING_DIR, config_file: Path = CONFIG_FILE):
        self.base_dir = base_dir
        self.config_file = config_file
        
        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._init_config()

    def _init_config(self) -> None:
        """Initialize configuration file if it doesn't exist"""
        if not self.config_file.exists():
            config = {
                "active_version": "default",
                "model_path": DEFAULT_BASE_MODEL,
                "deployed_at": None,
                "notes": "Default base model from SentenceTransformers"
            }
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                logger.info(f"Initialized active embedding config with default model: {DEFAULT_BASE_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize embedding active config: {e}")

    def get_active_config(self) -> Dict[str, Any]:
        """Load and return active version metadata config"""
        if not self.config_file.exists():
            self._init_config()
            
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading embedding config, falling back to default: {e}")
            return {
                "active_version": "default",
                "model_path": DEFAULT_BASE_MODEL
            }

    def get_current_model_path(self) -> str:
        """Get the active model path (either local directory or HuggingFace model hub ID)"""
        config = self.get_active_config()
        path = config.get("model_path", DEFAULT_BASE_MODEL)
        
        # Verify local model path exists, fallback if invalid
        if path != DEFAULT_BASE_MODEL and not Path(path).exists():
            logger.warning(f"Active model path '{path}' does not exist. Falling back to default '{DEFAULT_BASE_MODEL}'.")
            return DEFAULT_BASE_MODEL
            
        return path

    def get_current_model(self, device: Optional[str] = None) -> SentenceTransformer:
        """Load and return the active SentenceTransformer model"""
        model_path = self.get_current_model_path()
        logger.info(f"Loading active embedding model from: {model_path} on device: {device or 'default'}")
        
        try:
            # SentenceTransformer handles mapping to CUDA if device='cuda'
            return SentenceTransformer(model_path, device=device)
        except Exception as e:
            logger.error(f"Failed to load embedding model '{model_path}': {e}. Falling back to '{DEFAULT_BASE_MODEL}'.")
            return SentenceTransformer(DEFAULT_BASE_MODEL, device=device)

    def set_active_version(self, version: str, model_path: str, notes: Optional[str] = None) -> bool:
        """Switch the deployed model to a new version"""
        if not Path(model_path).exists() and model_path != DEFAULT_BASE_MODEL:
            logger.error(f"Cannot set active version. Model path does not exist: {model_path}")
            return False

        from datetime import datetime
        config = {
            "active_version": version,
            "model_path": str(model_path),
            "deployed_at": datetime.now().isoformat(),
            "notes": notes or f"Switched to version {version}"
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully switched deployed embedding model to {version} ({model_path})")
            return True
        except Exception as e:
            logger.error(f"Failed to save active version config: {e}")
            return False

    def get_all_versions(self) -> List[Dict[str, Any]]:
        """Scan directory and config file to return all available fine-tuned model versions"""
        versions = []
        
        # Add default base model
        versions.append({
            "version": "default",
            "model_path": DEFAULT_BASE_MODEL,
            "type": "base_model"
        })

        if not self.base_dir.exists():
            return versions

        # Scan folder for directories starting with 'version_' or 'embedding_'
        for item in sorted(self.base_dir.iterdir()):
            if item.is_dir() and (item.name.startswith("version_") or item.name.startswith("embedding_")):
                meta_file = item / "metadata.json"
                meta_data = {}
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            meta_data = json.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for version {item.name}: {e}")
                
                versions.append({
                    "version": item.name,
                    "model_path": str(item),
                    "type": "fine_tuned",
                    "metadata": meta_data
                })

        return versions

    def rollback_to(self, version: str) -> bool:
        """Rollback to a previously trained version"""
        if version == "default":
            return self.set_active_version("default", DEFAULT_BASE_MODEL, "Rollback to default SentenceTransformer")

        versions = self.get_all_versions()
        target = next((v for v in versions if v["version"] == version), None)
        
        if not target:
            logger.error(f"Cannot rollback. Version {version} not found in available models.")
            return False

        return self.set_active_version(
            version=version,
            model_path=target["model_path"],
            notes=f"Rollback to version {version}"
        )
