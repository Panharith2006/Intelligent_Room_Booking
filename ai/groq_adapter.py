"""
Groq API adapter for chatbot.
Groq provides free, fast LLM inference with models like Llama, Mixtral, and Gemma.
"""
import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    """Exception raised for Groq API errors."""
    pass


def call_groq(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
    timeout: int = 30
) -> str:
    """
    Call Groq API with the given prompt.
    
    Args:
        prompt: The user's input message
        api_key: Groq API key (defaults to GROQ_API_KEY env var)
        model: Model ID (defaults to GROQ_MODEL env var or llama3-8b-8192)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        timeout: Request timeout in seconds
    
    Returns:
        Generated text response from the model
    
    Raises:
        GroqError: If the API call fails
    """
    # Resolve credentials from environment if not provided
    api_key = api_key or os.environ.get('GROQ_API_KEY')
    model = model or os.environ.get('GROQ_MODEL') or 'llama3-8b-8192'
    
    if not api_key:
        raise GroqError("GROQ_API_KEY is required but not configured")
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepare payload (OpenAI-compatible format)
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        logger.debug(f"Calling Groq model: {model}")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=timeout)
        
        # Check for errors
        if response.status_code == 401:
            raise GroqError("Invalid Groq API key (401 Unauthorized)")
        elif response.status_code == 429:
            raise GroqError("Rate limit exceeded (429 Too Many Requests)")
        elif response.status_code >= 400:
            error_text = response.text[:500]
            raise GroqError(f"Groq API error {response.status_code}: {error_text}")
        
        # Parse response (OpenAI-compatible format)
        data = response.json()
        
        # Extract from OpenAI-compatible response
        if isinstance(data, dict) and 'choices' in data:
            choices = data['choices']
            if choices and len(choices) > 0:
                message = choices[0].get('message', {})
                content = message.get('content', '')
                if content:
                    return content.strip()
        
        # Fallback
        logger.warning(f"Unexpected Groq response format: {data}")
        return str(data).strip()
        
    except requests.exceptions.Timeout:
        raise GroqError(f"Request timeout after {timeout}s")
    except requests.exceptions.RequestException as e:
        raise GroqError(f"Request failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error calling Groq: {e}")
        raise GroqError(f"Failed to call Groq: {str(e)}")


async def call_groq_async(
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
    Async wrapper for call_groq.
    Accepts optional `session_id` and extra kwargs for compatibility with callers.
    Uses asyncio to run the synchronous HTTP call in a thread pool.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: call_groq(prompt, api_key, model, max_tokens, temperature, timeout)
    )
