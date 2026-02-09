import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from graphql_client import RetryItem

logger = logging.getLogger(__name__)


class RetryQueueManager:
    
    def __init__(self, queue_file: str = "retry_queue.json"):
        self.queue_file = Path(queue_file)
    
    def save_queue(self, retry_items: List[RetryItem]):
        try:
            queue_data = []
            for item in retry_items:
                queue_data.append({
                    "operation": item.operation,
                    "payload": item.payload,
                    "context": item.context,
                    "retry_count": item.retry_count,
                    "last_error": item.last_error,
                    "created_at": item.created_at.isoformat() if hasattr(item.created_at, 'isoformat') else str(item.created_at)
                })
            
            with open(self.queue_file, 'w') as f:
                json.dump(queue_data, f, indent=2)
            logger.info(f"[SAVE] Saved {len(retry_items)} items to retry queue file")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save retry queue: {e}")
    
    def load_queue(self) -> List[Dict[str, Any]]:
        if not self.queue_file.exists():
            return []
        
        try:
            with open(self.queue_file, 'r') as f:
                queue_data = json.load(f)
            logger.info(f"[LOADED] Loaded {len(queue_data)} items from retry queue file")
            return queue_data
        except Exception as e:
            logger.error(f"[ERROR] Failed to load retry queue: {e}")
            return []
    
    def clear_queue_file(self):
        try:
            if self.queue_file.exists():
                self.queue_file.unlink()
                logger.info("[CLEARED] Cleared retry queue file")
        except Exception as e:
            logger.error(f"[ERROR] Failed to clear retry queue file: {e}")

