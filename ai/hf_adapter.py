"""
Hugging Face Inference API adapter for chatbot.
Provides a free alternative to Deepseek using HF's hosted models.
"""
import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Hugging Face Serverless Inference API (text-generation-inference)
# Using the new dedicated inference API endpoint
HF_API_BASE = "https://api-inference.huggingface.co"


class HuggingFaceError(Exception):
    """Exception raised for Hugging Face API errors."""
    pass


def call_huggingface(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
    timeout: int = 30
) -> str:
    """
    Call Hugging Face Inference API with the given prompt.
    
    Args:
        prompt: The user's input message
        api_key: HF API token (defaults to HF_API_KEY env var)
        model: Model ID on Hugging Face (defaults to HF_MODEL env var)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        timeout: Request timeout in seconds
    
    Returns:
        Generated text response from the model
    
    Raises:
        HuggingFaceError: If the API call fails
    """
    # Resolve credentials from environment if not provided
    api_key = api_key or os.environ.get('HF_API_KEY')
    model = model or os.environ.get('HF_MODEL') or 'microsoft/DialoGPT-medium'
    
    if not api_key:
        raise HuggingFaceError("HF_API_KEY is required but not configured")
    
    # NOTE: As of Dec 2025, Hugging Face deprecated api-inference.huggingface.co
    # Free tier users must now use Inference Endpoints or consider alternatives
    # This adapter attempts to use the models via huggingface.co API
    url = f"https://huggingface.co/api/inference/models/{model}"
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # For chat/instruct models, format as a prompt
    formatted_prompt = f"<s>[INST] {prompt} [/INST]"
    
    # Prepare payload for text generation
    payload = {
        "inputs": formatted_prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "return_full_text": False
        }
    }
    
    try:
        logger.debug(f"Calling HuggingFace model: {model}")
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        
        # Check for errors
        if response.status_code == 401:
            raise HuggingFaceError("Invalid HF API key (401 Unauthorized)")
        elif response.status_code == 429:
            raise HuggingFaceError("Rate limit exceeded (429 Too Many Requests)")
        elif response.status_code == 404:
            raise HuggingFaceError(f"Model not found or doesn't support chat completions: {model}")
        elif response.status_code >= 400:
            error_text = response.text[:500]
            raise HuggingFaceError(f"HF API error {response.status_code}: {error_text}")
        
        # Parse response (text generation format)
        data = response.json()
        
        # Handle list response (standard text generation output)
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict) and 'generated_text' in first:
                return first['generated_text'].strip()
            elif isinstance(first, str):
                return first.strip()
        
        # Handle dict response
        if isinstance(data, dict):
            if 'generated_text' in data:
                return data['generated_text'].strip()
            elif 'error' in data:
                raise HuggingFaceError(f"HF API error: {data['error']}")
        
        # Fallback for non-standard responses
        logger.warning(f"Unexpected HF response format: {data}")
        return str(data).strip()
        
    except requests.exceptions.Timeout:
        raise HuggingFaceError(f"Request timeout after {timeout}s")
    except requests.exceptions.RequestException as e:
        raise HuggingFaceError(f"Request failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error calling HuggingFace: {e}")
        raise HuggingFaceError(f"Failed to call HuggingFace: {str(e)}")


async def call_huggingface_async(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
    timeout: int = 30,
    session_id: Optional[str] = None,
    **kwargs
) -> str:
    """
    Async wrapper for call_huggingface.
    Accepts optional `session_id` and extra kwargs for compatibility with callers.
    Uses asyncio to run the synchronous HTTP call in a thread pool.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: call_huggingface(prompt, api_key, model, max_tokens, temperature, timeout)
    )
