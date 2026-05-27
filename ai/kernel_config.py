import os
import logging
import time
import requests
from typing import Optional, List, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import ConfigDict

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings

logger = logging.getLogger(__name__)


# =========================
# GROQ INFERENCE API CONNECTOR (Recommended - Fast & Free)
# =========================
class GroqChatCompletion(ChatCompletionClientBase):
    """Groq API connector - faster inference than HuggingFace"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    service_id: str = "groq_chat"
    model_id: str = "llama-3.1-8b-instant"
    api_key: str = ""
    max_retries: int = 3
    timeout: int = 30
    session: Optional[Any] = None
    
    def __init__(self, model_id: str = None, api_key: str = None):
        super().__init__()
        self.model_id = model_id or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @property
    def ai_model_id(self) -> str:
        return self.model_id

    def __call__(self, prompt: str) -> str:
        """Call Groq API with synchronous request"""
        if not self.api_key:
            raise Exception("Groq API key not configured. Set GROQ_API_KEY env var.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = "https://api.groq.com/openai/v1/chat/completions"

        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 512,
            "top_p": 0.9,
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Groq request attempt {attempt + 1}/{self.max_retries}")
                response = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 401:
                    raise Exception("Groq API key invalid or expired")
                
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Groq rate limited (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code >= 400:
                    logger.error(f"Groq error {response.status_code}: {response.text}")
                    raise Exception(f"Groq error {response.status_code}: {response.text}")

                data = response.json()
                
                # Handle Groq response format (OpenAI compatible)
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Unexpected Groq response format: {data}")
                    return str(data)

            except requests.exceptions.Timeout as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(f"Groq timeout (attempt {attempt + 1}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            except requests.exceptions.ConnectionError as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(f"Groq connection error (attempt {attempt + 1}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            except Exception as e:
                last_error = e
                logger.exception(f"Groq error (attempt {attempt + 1}): {e}")
                raise
        
        raise Exception(f"Cannot connect to Groq after {self.max_retries} attempts. Last error: {last_error}")

    def generate(self, system: str = "", messages: List[Dict] = None) -> str:
        """Generate response using system prompt and message history"""
        if messages is None:
            messages = []
        
        # Build messages list for Groq API
        api_messages = []
        
        # Add system prompt if provided
        if system:
            api_messages.append({"role": "system", "content": system})
        
        # Add conversation history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                api_messages.append({"role": role, "content": content})
        
        if not api_messages:
            raise Exception("No messages to generate from")
        
        # Make API call
        api_key = self.api_key or os.getenv("GROQ_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        payload = {
            "model": self.model_id,
            "messages": api_messages,
            "temperature": 0.2,
            "max_tokens": 512,
        }
        
        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected response: {data}")
                return str(data)
        except Exception as e:
            logger.error(f"Groq generate error: {e}")
            raise

    async def get_chat_message_contents(
        self, chat_history: ChatHistory, settings: PromptExecutionSettings, **kwargs
    ):
        """Async wrapper for chat completions"""
        prompt = ""
        for msg in chat_history:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            prompt += f"{role}: {msg.content}\n"
        
        response_text = self.__call__(prompt)
        
        return [
            ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=response_text
            )
        ]

    async def get_streaming_chat_message_contents(
        self, chat_history: ChatHistory, settings: PromptExecutionSettings, **kwargs
    ):
        """Async wrapper for streaming (non-streaming fallback)"""
        messages = await self.get_chat_message_contents(chat_history, settings, **kwargs)
        for msg in messages:
            yield [msg]


def create_kernel_groq(
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> tuple:
    """Create Semantic Kernel with Groq LLM service"""
    
    model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    api_key = api_key or os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise Exception(
            "Groq API key not found!\n"
            "Set GROQ_API_KEY environment variable.\n"
            "Get your API key at: https://console.groq.com/keys"
        )

    kernel = Kernel()

    groq_service = GroqChatCompletion(model_id=model, api_key=api_key)
    kernel.add_service(groq_service)

    logger.info(f"✅ Groq Kernel initialized: {model}")
    logger.info("Using Groq API (fast inference)")

    return kernel, groq_service


# =========================
# HUGGINGFACE INFERENCE API CONNECTOR (Legacy - Commented Out)
# =========================
# class HuggingFaceChatCompletion(ChatCompletionClientBase):
#     """DEPRECATED: Use Groq instead for better performance"""
#     model_config = ConfigDict(arbitrary_types_allowed=True)
#     
#     service_id: str = "huggingface_chat"
#     model_id: str = "mistralai/Mistral-7B-Instruct-v0.1"
#     api_key: str = ""
#     use_inference_endpoint: bool = False
#     max_retries: int = 3
#     timeout: int = 60
#     session: Optional[Any] = None
#     
#     def __init__(self, model_id: str, api_key: str, use_inference_endpoint: bool = False):
#         super().__init__()
#         self.model_id = model_id
#         self.api_key = api_key
#         self.use_inference_endpoint = use_inference_endpoint
#         
#         self.session = requests.Session()
#         retry_strategy = Retry(
#             total=self.max_retries,
#             backoff_factor=0.5,
#             status_forcelist=[429, 500, 502, 503, 504],
#             allowed_methods=["POST", "GET"]
#         )
#         adapter = HTTPAdapter(max_retries=retry_strategy)
#         self.session.mount("http://", adapter)
#         self.session.mount("https://", adapter)
#
#     # [HuggingFace implementation commented out for brevity]


# Legacy function (kept for backward compatibility but uses Groq)
def create_kernel_huggingface(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    use_inference_endpoint: bool = False
) -> tuple:
    """DEPRECATED: Redirects to Groq. Use create_kernel_groq() instead."""
    logger.warning("create_kernel_huggingface is deprecated. Using Groq instead.")
    return create_kernel_groq(model=model, api_key=api_key)
