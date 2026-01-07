"""
Deepseek adapter using Semantic Kernel.
This adapter provides a sync `call_deepseek` function and an async
`call_deepseek_async` helper that uses Semantic Kernel for AI orchestration.
"""
import os
import asyncio
import time
import logging
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)


class DeepseekError(Exception):
    pass


# Lightweight in-process metrics (counters + timing)
_metrics_lock = Lock()
_deepseek_metrics = {
    'calls': 0,
    'successes': 0,
    'failures': 0,
    'retries': 0,
    'total_time_s': 0.0,
}


def _metric_inc(key: str, amount: int = 1):
    with _metrics_lock:
        if key in _deepseek_metrics:
            _deepseek_metrics[key] += amount


def _metric_time_add(seconds: float):
    with _metrics_lock:
        _deepseek_metrics['total_time_s'] += seconds


def get_deepseek_metrics() -> dict:
    """Return a snapshot of Deepseek adapter metrics."""
    with _metrics_lock:
        snapshot = dict(_deepseek_metrics)
    # add derived metric: avg_latency
    calls = snapshot.get('successes', 0)
    snapshot['avg_latency_s'] = (snapshot['total_time_s'] / calls) if calls > 0 else None
    return snapshot


def call_deepseek(prompt: str, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = 'deepseek-chat', session_id: Optional[str] = None, retries: int = 2, backoff_factor: float = 0.5, timeout: int = 30) -> str:
    """Call Deepseek via Semantic Kernel synchronously.
    
    This function wraps the async kernel call for backward compatibility.
    """
    try:
        # Run async call in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                call_deepseek_async(prompt, api_key, base_url, model, session_id, retries, backoff_factor, timeout)
            )
            return result
        finally:
            loop.close()
    except Exception as e:
        logger.exception(f"Error in call_deepseek: {e}")
        if isinstance(e, DeepseekError):
            raise
        raise DeepseekError(f"Failed to call Deepseek: {str(e)}")


async def call_deepseek_async(prompt: str, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = 'deepseek-chat', session_id: Optional[str] = None, retries: int = 2, backoff_factor: float = 0.5, timeout: int = 30) -> str:
    """Call Deepseek via Semantic Kernel asynchronously."""
    from ai.kernel_config import create_kernel
    from semantic_kernel.contents.chat_history import ChatHistory
    from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
    
    _metric_inc('calls', 1)
    start_time = time.time()
    
    try:
        # Create kernel with Deepseek connector
        kernel = create_kernel(api_key=api_key, base_url=base_url)
        
        # Create chat history with user prompt
        chat_history = ChatHistory()
        chat_history.add_user_message(prompt)
        
        # Create execution settings
        settings = PromptExecutionSettings(
            max_tokens=512,
            temperature=0.2,
            top_p=1.0
        )
        
        # Get chat completion service
        chat_service = kernel.get_service()
        
        # Invoke the chat service
        response = await chat_service.get_chat_message_contents(
            chat_history=chat_history,
            settings=settings
        )
        
        # Extract text from response
        if response and len(response) > 0:
            result = response[0].content if hasattr(response[0], 'content') else str(response[0])
            
            # Record success metrics
            elapsed = time.time() - start_time
            _metric_inc('successes', 1)
            _metric_time_add(elapsed)
            
            logger.debug(f"Deepseek response via SK (session={session_id}): {result[:200]}...")
            return result
        else:
            raise DeepseekError("Empty response from Deepseek")
            
    except Exception as e:
        elapsed = time.time() - start_time
        _metric_inc('failures', 1)
        _metric_time_add(elapsed)
        
        logger.exception(f"Deepseek call via SK failed: {e}")
        if isinstance(e, DeepseekError):
            raise
        raise DeepseekError(f"Failed to call Deepseek via Semantic Kernel: {str(e)}")
