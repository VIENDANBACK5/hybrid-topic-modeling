import json
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class ObjectStore:
    def __init__(self, base_dir: str = "data/objects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, key: str, data: Any, format: str = 'json') -> str:
        file_path = self.base_dir / f"{key}.{format}"
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(file_path, 'wb') as f:
                f.write(data)
        
        logger.info(f"Saved {key} to {file_path}")
        return str(file_path)
    
    def load(self, key: str, format: str = 'json') -> Optional[Any]:
        file_path = self.base_dir / f"{key}.{format}"
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        
        if format == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(file_path, 'rb') as f:
                return f.read()
    
    def exists(self, key: str, format: str = 'json') -> bool:
        file_path = self.base_dir / f"{key}.{format}"
        return file_path.exists()
    
    def delete(self, key: str, format: str = 'json') -> bool:
        file_path = self.base_dir / f"{key}.{format}"
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted {file_path}")
            return True
        return False
