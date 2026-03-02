import os
import logging
from typing import Optional
import requests
import json
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.kernel_pydantic import KernelBaseModel

logger = logging.getLogger(__name__)

# ============================================================================  
# OLLAMA LOCAL MODEL CONNECTOR  
# ============================================================================  

class OllamaChatCompletion(ChatCompletionClientBase, KernelBaseModel):
    """Custom Ollama Chat Completion connector for Semantic Kernel (Local LLM)."""

    model_id: str = "gemma3:1b"
    base_url: str = "http://localhost:11434"
    _ai_model_id: str = ""

    def model_post_init(self, __context) -> None:
        """Post-initialization to set computed fields."""
        if not self._ai_model_id:
            object.__setattr__(self, "_ai_model_id", self.model_id)

    @property
    def ai_model_id(self) -> str:
        return self._ai_model_id

    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs
    ) -> list[ChatMessageContent]:
        """Get chat message contents from local Ollama API."""

        # Convert chat history to Ollama message format
        messages = []
        for msg in chat_history.messages:
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            content = msg.content if hasattr(msg, "content") else str(msg)
            if role in ["system", "user", "assistant"]:
                messages.append({"role": role, "content": content})

        # Build request payload
        endpoint = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": getattr(settings, "max_tokens", 512),
                "temperature": getattr(settings, "temperature", 0.7),
            },
        }

        import time
        from requests.exceptions import ReadTimeout, ConnectionError

        # Retry with exponential backoff for transient slow responses
        max_retries = 3
        base_timeout = 120  # seconds per request (increased)
        backoff_factor = 1.5

        last_exc = None
        logger.debug(f"Calling Ollama endpoint: {endpoint} with model: {self.model_id}")

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(endpoint, json=payload, timeout=base_timeout)

                if response.status_code == 404:
                    raise Exception(
                        f"Model '{self.model_id}' not found in Ollama. Pull it first: `ollama pull {self.model_id}`"
                    )
                elif response.status_code >= 400:
                    raise Exception(f"Ollama API error {response.status_code}: {response.text}")

                data = response.json()

                # Extract text from Ollama response
                if isinstance(data, dict) and "message" in data:
                    message = data["message"]
                    text = message.get("content", "") if isinstance(message, dict) else ""
                    from semantic_kernel.contents.utils.author_role import AuthorRole
                    return [ChatMessageContent(role=AuthorRole.ASSISTANT, content=text)]

                # Fallback
                from semantic_kernel.contents.utils.author_role import AuthorRole
                return [ChatMessageContent(role=AuthorRole.ASSISTANT, content="I'm processing your request.")]

            except ReadTimeout as e:
                last_exc = e
                logger.warning(f"Ollama read timeout on attempt {attempt}/{max_retries}: {e}")
                if attempt < max_retries:
                    sleep_time = backoff_factor ** attempt
                    logger.debug(f"Retrying after {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    continue
                else:
                    raise Exception(
                        f"Ollama server did not respond within {base_timeout}s after {max_retries} attempts.\n"
                        "Check that Ollama is running, the model is loaded, or increase timeout."
                    )

            except ConnectionError:
                raise Exception("Cannot connect to Ollama server. Make sure Ollama is running: `ollama serve`")

            except Exception as e:
                # For other exceptions, log and re-raise
                logger.exception(f"Error calling Ollama: {e}")
                raise

    async def get_streaming_chat_message_contents(
        self, chat_history: ChatHistory, settings: PromptExecutionSettings, **kwargs
    ):
        """Streaming not implemented, fallback to non-streaming"""
        messages = await self.get_chat_message_contents(chat_history, settings, **kwargs)
        for msg in messages:
            yield [msg]


# ============================================================================  
# KERNEL CREATION FUNCTION (LOCAL ONLY)  
# ============================================================================  

def create_kernel_ollama(model: Optional[str] = None, base_url: Optional[str] = None) -> Kernel:
    if not model:
        model = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
    if not base_url:
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    kernel = Kernel()
    ollama_service = OllamaChatCompletion(model_id=model, base_url=base_url)
    kernel.add_service(ollama_service)

    logger.info(f"Semantic Kernel initialized with Ollama (model: {model}, url: {base_url})")
    return kernel