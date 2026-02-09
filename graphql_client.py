import json
import asyncio
import random
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class RetryItem:
    operation: str
    payload: Dict[str, Any]
    context: Dict[str, Any]
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class GraphQLClient:
    
    def __init__(
        self,
        page,
        timeout: int = 120000,
        max_retries: int = 5,
        base_backoff: float = 1.0,
        max_backoff: float = 60.0,
        min_pacing: float = 0.5,
        max_pacing: float = 3.0,
        retry_queue_max_size: int = 100
    ):
        self.page = page
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.min_pacing = min_pacing
        self.max_pacing = max_pacing
        self.retry_queue: List[RetryItem] = []
        self.retry_queue_max_size = retry_queue_max_size
        self.graphql_url = "https://app.estimateone.com/graphql/subbie"
    
    def _validate_response(self, response_data: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not isinstance(response_data, dict):
            ctx_str = self._format_context(context)
            return False, f"Invalid response format: expected dict, got {type(response_data).__name__} [{ctx_str}]"
        
        if "errors" in response_data and response_data["errors"]:
            errors = response_data["errors"]
            error_messages = [err.get("message", str(err)) for err in errors]
            ctx_str = self._format_context(context)
            return False, f"GraphQL errors: {', '.join(error_messages)} [{ctx_str}]"
        
        if "data" not in response_data:
            ctx_str = self._format_context(context)
            return False, f"Missing 'data' field in response [{ctx_str}]"
        
        return True, None
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        parts = []
        if "page_number" in context:
            parts.append(f"page={context['page_number']}")
        if "project_id" in context:
            parts.append(f"project_id={context['project_id']}")
        if "operation" in context:
            parts.append(f"operation={context['operation']}")
        return ", ".join(parts) if parts else "unknown"
    
    async def _exponential_backoff(self, retry_count: int):
        backoff_time = min(
            self.base_backoff * (2 ** retry_count),
            self.max_backoff
        )
        jitter = backoff_time * 0.2 * random.random()
        wait_time = backoff_time + jitter
        logger.info(f"⏳ Backing off for {wait_time:.2f}s (retry {retry_count + 1}/{self.max_retries})")
        await asyncio.sleep(wait_time)
    
    async def _random_pacing(self):
        if self.max_pacing > 0:
            delay = random.uniform(self.min_pacing, self.max_pacing)
            await asyncio.sleep(delay)
    
    async def _make_request(
        self,
        payload: Dict[str, Any],
        context: Dict[str, Any],
        retry_count: int = 0
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[int]]:
        ctx_str = self._format_context(context)
        
        try:
            await self._random_pacing()
            
            logger.info(f"[GraphQL] GraphQL request: {payload.get('operationName', 'unknown')} [{ctx_str}]")
            
            response = await self.page.request.post(
                self.graphql_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            status = response.status
            if status != 200:
                error_msg = f"HTTP {status}: {response.status_text} [{ctx_str}]"
                logger.error(f"[ERROR] {error_msg}")
                return None, error_msg, status
            
            response_text = await response.text()
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                error_msg = f"JSON decode error: {str(e)} [{ctx_str}]"
                logger.error(f"[ERROR] {error_msg}")
                return None, error_msg, status
            
            is_valid, error_msg = self._validate_response(response_data, context)
            if not is_valid:
                logger.error(f"[ERROR] Validation failed: {error_msg}")
                return None, error_msg, status
            
            logger.info(f"[OK] GraphQL request successful: {payload.get('operationName', 'unknown')} [{ctx_str}]")
            return response_data, None, status
            
        except asyncio.TimeoutError:
            error_msg = f"Request timeout after {self.timeout/1000}s [{ctx_str}]"
            logger.error(f"[ERROR] {error_msg}")
            return None, error_msg, None
        except Exception as e:
            error_msg = f"Request exception: {str(e)} [{ctx_str}]"
            logger.error(f"[ERROR] {error_msg}")
            return None, error_msg, None
    
    async def execute(
        self,
        payload: Dict[str, Any],
        context: Dict[str, Any],
        auto_retry: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[int]]:
        retry_count = 0
        last_error = None
        last_status = None
        
        while retry_count <= self.max_retries:
            response_data, error, http_status = await self._make_request(payload, context, retry_count)
            
            if response_data is not None:
                return response_data, None, http_status
            
            last_error = error
            last_status = http_status
            
            if not auto_retry or retry_count >= self.max_retries:
                break
            
            retry_count += 1
            await self._exponential_backoff(retry_count - 1)
        
        if auto_retry and len(self.retry_queue) < self.retry_queue_max_size:
            retry_item = RetryItem(
                operation=payload.get('operationName', 'unknown'),
                payload=payload,
                context=context,
                retry_count=retry_count,
                last_error=last_error
            )
            self.retry_queue.append(retry_item)
            ctx_str = self._format_context(context)
            logger.warning(f"[WARNING] Added to retry queue (size: {len(self.retry_queue)}/{self.retry_queue_max_size}) [{ctx_str}]")
        
        ctx_str = self._format_context(context)
        logger.error(f"[ERROR] All retries exhausted ({retry_count}/{self.max_retries}) [{ctx_str}]: {last_error}")
        return None, last_error, last_status
    
    async def process_retry_queue(self) -> Dict[str, int]:
        stats = {'success': 0, 'failed': 0, 'processed': 0}
        
        if not self.retry_queue:
            return stats
        
        logger.info(f"[RETRY] Processing retry queue ({len(self.retry_queue)} items)")
        
        items_to_retry = list(self.retry_queue)
        self.retry_queue.clear()
        
        for item in items_to_retry:
            stats['processed'] += 1
            ctx_str = self._format_context(item.context)
            logger.info(f"[RETRY] Retrying queued item: {item.operation} [{ctx_str}] (previous retries: {item.retry_count})")
            
            response_data, error, http_status = await self.execute(
                item.payload,
                item.context,
                auto_retry=False
            )
            
            if response_data is not None:
                stats['success'] += 1
                logger.info(f"[OK] Retry successful: {item.operation} [{ctx_str}]")
            else:
                stats['failed'] += 1
                logger.error(f"[ERROR] Retry failed: {item.operation} [{ctx_str}]: {error}")
        
        logger.info(f"[STATS] Retry queue processing complete: {stats['success']} success, {stats['failed']} failed, {stats['processed']} total")
        return stats
    
    def get_retry_queue_size(self) -> int:
        return len(self.retry_queue)
    
    def clear_retry_queue(self):
        self.retry_queue.clear()
        logger.info("[CLEARED] Retry queue cleared")

