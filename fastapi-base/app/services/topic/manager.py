"""
Model manager with lazy loading and caching
"""
from pathlib import Path
from typing import Optional
import logging
from app.core.cache import cached

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton model manager with lazy loading and caching
    Prevents multiple models from being loaded simultaneously
    """
    
    _instance = None
    _model = None
    _current_model_name = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.model_dir = Path("data/models")
            self.initialized = True
            logger.info("ModelManager initialized")
    
    def get_model(self, model_name: Optional[str] = None):
        """
        Get model with lazy loading
        
        Args:
            model_name: Specific model name, or None for auto-load
        
        Returns:
            TopicModel instance
        """
        # If model already loaded and same name, return cached
        if self._model is not None:
            if model_name is None or model_name == self._current_model_name:
                logger.debug(f"Using cached model: {self._current_model_name}")
                return self._model
        
        # Load new model
        from app.services.topic.model import TopicModel
        
        if self._model is None:
            logger.info("Loading model for first time")
            self._model = TopicModel()
        
        # Auto-load or load specific model
        if model_name:
            logger.info(f"Loading specific model: {model_name}")
            self._model.load(model_name)
            self._current_model_name = model_name
        else:
            logger.info("Auto-loading best available model")
            self._model._auto_load_model()
            self._current_model_name = self._get_loaded_model_name()
        
        return self._model
    
    def _get_loaded_model_name(self) -> Optional[str]:
        """Get name of currently loaded model"""
        if self._model and self._model.topic_model:
            # Try to infer from model directory
            # This is a best-effort guess
            return "auto_loaded"
        return None
    
    def reload_model(self, model_name: Optional[str] = None):
        """Force reload model (useful after training)"""
        logger.info(f"Reloading model: {model_name or 'auto'}")
        self._model = None
        self._current_model_name = None
        return self.get_model(model_name)
    
    def clear_cache(self):
        """Clear cached model"""
        logger.info("Clearing model cache")
        self._model = None
        self._current_model_name = None


# Global model manager instance
model_manager = ModelManager()
