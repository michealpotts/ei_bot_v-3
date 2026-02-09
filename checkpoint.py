import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

CHECKPOINT_FILE = "scraper_checkpoint.json"


class CheckpointManager:
    
    def __init__(self, checkpoint_file: str = CHECKPOINT_FILE):
        self.checkpoint_file = Path(checkpoint_file)
    
    def save_checkpoint(self, page_number: int, project_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        existing = self.load_checkpoint()
        scraped_ids = set(existing.get('scraped_ids', [])) if existing else set()
        
        if project_id:
            scraped_ids.add(project_id)
        
        checkpoint = {
            "page_number": page_number,
            "project_id": project_id,
            "scraped_ids": list(scraped_ids),
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            logger.info(f"[SAVE] Checkpoint saved: page={page_number}, project_id={project_id}, total_scraped={len(scraped_ids)}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        if not self.checkpoint_file.exists():
            logger.info("[INFO] No checkpoint file found")
            return None
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            logger.info(f"[LOADED] Checkpoint loaded: page={checkpoint.get('page_number')}, project_id={checkpoint.get('project_id')}")
            return checkpoint
        except Exception as e:
            logger.error(f"[ERROR] Failed to load checkpoint: {e}")
            return None
    
    def clear_checkpoint(self):
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info("[CLEARED] Checkpoint cleared")
        except Exception as e:
            logger.error(f"[ERROR] Failed to clear checkpoint: {e}")
    
    def get_resume_page(self, default_start: int = 1) -> int:
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('page_number', default_start)
        return default_start
    
    def get_last_project_id(self) -> Optional[str]:
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('project_id')
        return None
    
    def is_project_scraped(self, project_id: str) -> bool:
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return False
        
        scraped_ids = set(checkpoint.get('scraped_ids', []))
        return project_id in scraped_ids
    
    def get_scraped_project_ids(self) -> set:
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return set()
        return set(checkpoint.get('scraped_ids', []))

