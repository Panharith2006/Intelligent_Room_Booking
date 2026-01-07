"""
Semantic Kernel configuration and initialization for Deepseek integration.
"""
import os
import logging
from typing import Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.kernel_pydantic import KernelBaseModel
import requests
import json

logger = logging.getLogger(__name__)


class DeepseekChatCompletion(ChatCompletionClientBase, KernelBaseModel):
    """Custom Deepseek Chat Completion connector for Semantic Kernel."""
    
    api_key: str
    base_url: str
    model_id: str = "deepseek-chat"
    endpoint: str = ""
    _ai_model_id: str = ""
    
    def model_post_init(self, __context) -> None:
        """Post-initialization to set computed fields."""
        # Normalize base_url
        normalized_base = self.base_url.rstrip('/')
        object.__setattr__(self, 'base_url', normalized_base)
        
        # Set ai_model_id
        if not self._ai_model_id:
            object.__setattr__(self, '_ai_model_id', self.model_id)
        
        # Determine endpoint
        if normalized_base.endswith('/v3'):
            endpoint = f"{normalized_base}/analyze"
        elif normalized_base.endswith('/analyze') or normalized_base.endswith('/completions') or normalized_base.endswith('/chat/completions'):
            endpoint = normalized_base
        else:
            endpoint = f"{normalized_base}/chat/completions"
        
        object.__setattr__(self, 'endpoint', endpoint)
    
    @property
    def ai_model_id(self) -> str:
        return self._ai_model_id
    
    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs
    ) -> list[ChatMessageContent]:
        """Get chat message contents from Deepseek API."""
        
        # Convert chat history to messages format
        messages = []
        for msg in chat_history.messages:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            content = msg.content if hasattr(msg, 'content') else str(msg)
            messages.append({"role": role, "content": content})
        
        # Build request payload
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": getattr(settings, 'max_tokens', 512),
            "temperature": getattr(settings, 'temperature', 0.2),
            "top_p": getattr(settings, 'top_p', 1.0),
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        try:
            logger.debug(f"Calling Deepseek endpoint: {self.endpoint}")
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code >= 400:
                logger.error(f"Deepseek API error {response.status_code}: {response.text[:500]}")
                raise Exception(f"Deepseek API error {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Extract response text
            text = None
            if isinstance(data, dict):
                choices = data.get('choices', [])
                if choices and len(choices) > 0:
                    first_choice = choices[0]
                    message = first_choice.get('message', {})
                    text = message.get('content') or first_choice.get('text')
                
                if not text:
                    text = data.get('result') or data.get('text') or json.dumps(data)
            
            # Return as ChatMessageContent
            from semantic_kernel.contents.chat_message_content import ChatMessageContent
            from semantic_kernel.contents.utils.author_role import AuthorRole
            
            return [ChatMessageContent(role=AuthorRole.ASSISTANT, content=text or "")]
            
        except Exception as e:
            logger.exception(f"Error calling Deepseek: {e}")
            raise
    
    async def get_streaming_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs
    ):
        """Streaming not implemented - fallback to non-streaming."""
        messages = await self.get_chat_message_contents(chat_history, settings, **kwargs)
        for msg in messages:
            yield [msg]


def create_kernel(api_key: Optional[str] = None, base_url: Optional[str] = None) -> Kernel:
    """Create and configure a Semantic Kernel instance with Deepseek."""
    
    # Resolve configuration from environment if not provided
    if not api_key:
        api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not base_url:
        base_url = os.environ.get('DEEPSEEK_BASE_URL') or os.environ.get('DEEPSEEK_API_URL')
    
    if not api_key or not base_url:
        raise ValueError("DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL must be configured")
    
    # Create kernel
    kernel = Kernel()
    
    # Add Deepseek chat completion service
    deepseek_service = DeepseekChatCompletion(
        api_key=api_key,
        base_url=base_url,
        model_id="deepseek-chat"
    )
    
    kernel.add_service(deepseek_service)
    
    logger.info("Semantic Kernel initialized with Deepseek connector")
    return kernel


# Global kernel instance (lazy initialization)
_kernel_instance: Optional[Kernel] = None


def get_kernel() -> Kernel:
    """Get or create the global kernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = create_kernel()
    return _kernel_instance
