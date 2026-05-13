import os
import logging
import time
import requests
from typing import Optional, List

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings

logger = logging.getLogger(__name__)


# =========================
# OLLAMA CONNECTOR
# =========================

class OllamaChatCompletion(ChatCompletionClientBase):
    """
    Lightweight Ollama connector for Semantic Kernel (production-safe version)
    """

    service_id: str = "ollama_chat"
    model_id: str = "gemma3:1b"
    base_url: str = "http://localhost:11434"

    @property
    def ai_model_id(self) -> str:
        return self.model_id

    def __call__(self, prompt: str) -> str:
        """Synchronous prompt interface used by QueryProcessor and SelfRAG."""
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 1024,
            },
        }

        url = f"{self.base_url.rstrip('/')}/api/chat"
        response = requests.post(url, json=payload, timeout=120)

        if response.status_code == 404:
            raise Exception(f"Model not found: {self.model_id}")

        if response.status_code >= 400:
            raise Exception(f"Ollama error: {response.text}")

        data = response.json()
        return data.get("message", {}).get("content", "")

    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs
    ) -> List[ChatMessageContent]:

        messages = []
        for msg in chat_history.messages:
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            content = getattr(msg, "content", str(msg))

            if role in ["system", "user", "assistant"]:
                messages.append({"role": role, "content": content})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": getattr(settings, "temperature", 0.7),
                "num_predict": getattr(settings, "max_tokens", 512),
            },
        }

        url = f"{self.base_url.rstrip('/')}/api/chat"

        max_retries = 3
        timeout = 120

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=timeout)

                if response.status_code == 404:
                    raise Exception(f"Model not found: {self.model_id}")

                if response.status_code >= 400:
                    raise Exception(f"Ollama error: {response.text}")

                data = response.json()
                content = data.get("message", {}).get("content", "")

                return [ChatMessageContent(role=AuthorRole.ASSISTANT, content=content)]

            except requests.exceptions.ReadTimeout:
                logger.warning(f"Ollama timeout attempt {attempt + 1}")
                time.sleep(2 ** attempt)

            except requests.exceptions.ConnectionError:
                raise Exception("Cannot connect to Ollama. Run: `ollama serve`")

            except Exception as e:
                logger.exception(f"Ollama error: {e}")
                raise

        return [
            ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content="Sorry, the AI model is not responding right now."
            )
        ]

    async def get_streaming_chat_message_contents(
        self, chat_history: ChatHistory, settings: PromptExecutionSettings, **kwargs
    ):
        messages = await self.get_chat_message_contents(chat_history, settings, **kwargs)
        for msg in messages:
            yield [msg]


# =========================
# KERNEL FACTORY
# =========================

def create_kernel_ollama(
    model: Optional[str] = None,
    base_url: Optional[str] = None
) -> Kernel:

    model = model or os.getenv("OLLAMA_MODEL", "gemma3:1b")
    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    kernel = Kernel()

    ollama_service = OllamaChatCompletion(
        model_id=model,
        base_url=base_url
    )

    kernel.add_service(ollama_service)
    kernel.llm_client = ollama_service

    logger.info(f"Ollama Kernel initialized: {model} @ {base_url}")

    return kernel