"""
Semantic Kernel configuration and initialization for Groq integration.
(Deepseek paths are commented out)
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


class GroqChatCompletion(ChatCompletionClientBase, KernelBaseModel):
    """Custom Groq Chat Completion connector for Semantic Kernel."""
    
    api_key: str
    model_id: str = "llama-3.1-8b-instant"
    endpoint: str = "https://api.groq.com/openai/v1/chat/completions"
    _ai_model_id: str = ""
    
    def model_post_init(self, __context) -> None:
        """Post-initialization to set computed fields."""
        # Set ai_model_id
        if not self._ai_model_id:
            object.__setattr__(self, '_ai_model_id', self.model_id)
    
    @property
    def ai_model_id(self) -> str:
        return self._ai_model_id
    
    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
        **kwargs
    ) -> list[ChatMessageContent]:
        """Get chat message contents from Groq API."""
        
        # Convert chat history to messages format
        messages = []
        for msg in chat_history.messages:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            content = msg.content if hasattr(msg, 'content') else str(msg)
            
            # Handle different message types
            if role == 'tool':
                # Tool/function result message
                msg_dict = {
                    "role": "tool",
                    "content": content,
                    "tool_call_id": msg.metadata.get('tool_call_id', '') if hasattr(msg, 'metadata') else ''
                }
            elif hasattr(msg, 'items') and msg.items:
                # Message with tool calls
                msg_dict = {"role": role, "content": content or ''}
                tool_calls = []
                for item in msg.items:
                    if hasattr(item, 'id') and hasattr(item, 'name'):  # FunctionCallContent
                        tool_calls.append({
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.name,
                                "arguments": item.arguments if hasattr(item, 'arguments') else '{}'
                            }
                        })
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
            else:
                # Regular message
                msg_dict = {"role": role, "content": content}
            
            messages.append(msg_dict)
        
        # Build request payload (OpenAI-compatible format)
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": getattr(settings, 'max_tokens', 512),
            "temperature": getattr(settings, 'temperature', 0.7),
        }
        
        # Add tools/functions if provided in kwargs
        if 'tools' in kwargs and kwargs['tools']:
            payload['tools'] = kwargs['tools']
            payload['tool_choice'] = 'auto'
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        try:
            logger.debug(f"Calling Groq endpoint: {self.endpoint}")
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code >= 400:
                logger.error(f"Groq API error {response.status_code}: {response.text[:500]}")
                raise Exception(f"Groq API error {response.status_code}: {response.text}")
            
            data = response.json()
            
            logger.info(f"Groq raw response: {json.dumps(data)[:500]}")
            
            # Extract response (OpenAI-compatible format)
            from semantic_kernel.contents.chat_message_content import ChatMessageContent
            from semantic_kernel.contents.utils.author_role import AuthorRole
            from semantic_kernel.contents.function_call_content import FunctionCallContent
            
            if isinstance(data, dict):
                choices = data.get('choices', [])
                if choices and len(choices) > 0:
                    first_choice = choices[0]
                    message = first_choice.get('message', {})
                    
                    # Check for tool calls
                    tool_calls = message.get('tool_calls', [])
                    if tool_calls:
                        # Create ChatMessageContent with function calls
                        items = []
                        for tool_call in tool_calls:
                            if tool_call.get('type') == 'function':
                                func_data = tool_call.get('function', {})
                                items.append(FunctionCallContent(
                                    id=tool_call.get('id', ''),
                                    name=func_data.get('name', ''),
                                    arguments=func_data.get('arguments', '{}')
                                ))
                        
                        return [ChatMessageContent(
                            role=AuthorRole.ASSISTANT,
                            items=items,
                            content=message.get('content', '')
                        )]
                    
                    # No tool calls, just text response
                    text = message.get('content') or first_choice.get('text') or ''
                    logger.info(f"Groq text response: {text[:200] if text else 'empty'}")
                    return [ChatMessageContent(role=AuthorRole.ASSISTANT, content=text)]
            
            # Fallback - log warning
            logger.warning(f"Unexpected Groq response format: {data}")
            return [ChatMessageContent(role=AuthorRole.ASSISTANT, content="I'm processing your request.")]
            
        except Exception as e:
            logger.exception(f"Error calling Groq: {e}")
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


# COMMENTED OUT: Deepseek connector (replaced with Groq)
# class DeepseekChatCompletion(ChatCompletionClientBase, KernelBaseModel):
#     """Custom Deepseek Chat Completion connector for Semantic Kernel."""
#     
#     api_key: str
#     base_url: str
#     model_id: str = "deepseek-chat"
#     endpoint: str = ""
#     _ai_model_id: str = ""
#     
#     def model_post_init(self, __context) -> None:
#         """Post-initialization to set computed fields."""
#         # Normalize base_url
#         normalized_base = self.base_url.rstrip('/')
#         object.__setattr__(self, 'base_url', normalized_base)
#         
#         # Set ai_model_id
#         if not self._ai_model_id:
#             object.__setattr__(self, '_ai_model_id', self.model_id)
#         
#         # Determine endpoint
#         if normalized_base.endswith('/v3'):
#             endpoint = f"{normalized_base}/analyze"
#         elif normalized_base.endswith('/analyze') or normalized_base.endswith('/completions') or normalized_base.endswith('/chat/completions'):
#             endpoint = normalized_base
#         else:
#             endpoint = f"{normalized_base}/chat/completions"
#         
#         object.__setattr__(self, 'endpoint', endpoint)
#     
#     @property
#     def ai_model_id(self) -> str:
#         return self._ai_model_id
#     
#     async def get_chat_message_contents(
#         self,
#         chat_history: ChatHistory,
#         settings: PromptExecutionSettings,
#         **kwargs
#     ) -> list[ChatMessageContent]:
#         """Get chat message contents from Deepseek API."""
#         
#         # Convert chat history to messages format
#         messages = []
#         for msg in chat_history.messages:
#             role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
#             content = msg.content if hasattr(msg, 'content') else str(msg)
#             messages.append({"role": role, "content": content})
#         
#         # Build request payload
#         payload = {
#             "model": self.model_id,
#             "messages": messages,
#             "max_tokens": getattr(settings, 'max_tokens', 512),
#             "temperature": getattr(settings, 'temperature', 0.2),
#             "top_p": getattr(settings, 'top_p', 1.0),
#         }
#         
#         headers = {
#             'Content-Type': 'application/json',
#             'Accept': 'application/json',
#             'Authorization': f'Bearer {self.api_key}'
#         }
#         
#         try:
#             logger.debug(f"Calling Deepseek endpoint: {self.endpoint}")
#             response = requests.post(
#                 self.endpoint,
#                 headers=headers,
#                 json=payload,
#                 timeout=30
#             )
#             
#             if response.status_code >= 400:
#                 logger.error(f"Deepseek API error {response.status_code}: {response.text[:500]}")
#                 raise Exception(f"Deepseek API error {response.status_code}: {response.text}")
#             
#             data = response.json()
#             
#             # Extract response text
#             text = None
#             if isinstance(data, dict):
#                 choices = data.get('choices', [])
#                 if choices and len(choices) > 0:
#                     first_choice = choices[0]
#                     message = first_choice.get('message', {})
#                     text = message.get('content') or first_choice.get('text')
#                 
#                 if not text:
#                     text = data.get('result') or data.get('text') or json.dumps(data)
#             
#             # Return as ChatMessageContent
#             from semantic_kernel.contents.chat_message_content import ChatMessageContent
#             from semantic_kernel.contents.utils.author_role import AuthorRole
#             
#             return [ChatMessageContent(role=AuthorRole.ASSISTANT, content=text or "")]
#             
#         except Exception as e:
#             logger.exception(f"Error calling Deepseek: {e}")
#             raise
#     
#     async def get_streaming_chat_message_contents(
#         self,
#         chat_history: ChatHistory,
#         settings: PromptExecutionSettings,
#         **kwargs
#     ):
#         """Streaming not implemented - fallback to non-streaming."""
#         messages = await self.get_chat_message_contents(chat_history, settings, **kwargs)
#         for msg in messages:
#             yield [msg]


def create_kernel(api_key: Optional[str] = None, model: Optional[str] = None) -> Kernel:
    """Create and configure a Semantic Kernel instance with Groq."""
    
    # Resolve configuration from Django settings or environment
    if not api_key:
        try:
            from django.conf import settings
            api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')
        except Exception:
            api_key = os.environ.get('GROQ_API_KEY')
    
    if not model:
        try:
            from django.conf import settings
            model = getattr(settings, 'GROQ_MODEL', None) or os.environ.get('GROQ_MODEL') or 'llama-3.1-8b-instant'
        except Exception:
            model = os.environ.get('GROQ_MODEL') or 'llama-3.1-8b-instant'
    
    if not api_key:
        raise ValueError("GROQ_API_KEY must be configured")
    
    # Create kernel
    kernel = Kernel()
    
    # Add Groq chat completion service
    groq_service = GroqChatCompletion(
        api_key=api_key,
        model_id=model
    )
    
    kernel.add_service(groq_service)
    
    logger.info(f"Semantic Kernel initialized with Groq connector (model: {model})")
    return kernel


# COMMENTED OUT: Deepseek kernel creation
# def create_kernel_deepseek(api_key: Optional[str] = None, base_url: Optional[str] = None) -> Kernel:
#     """Create and configure a Semantic Kernel instance with Deepseek."""
#     
#     # Resolve configuration from environment if not provided
#     if not api_key:
#         api_key = os.environ.get('DEEPSEEK_API_KEY')
#     if not base_url:
#         base_url = os.environ.get('DEEPSEEK_BASE_URL') or os.environ.get('DEEPSEEK_API_URL')
#     
#     if not api_key or not base_url:
#         raise ValueError("DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL must be configured")
#     
#     # Create kernel
#     kernel = Kernel()
#     
#     # Add Deepseek chat completion service
#     deepseek_service = DeepseekChatCompletion(
#         api_key=api_key,
#         base_url=base_url,
#         model_id="deepseek-chat"
#     )
#     
#     kernel.add_service(deepseek_service)
#     
#     logger.info("Semantic Kernel initialized with Deepseek connector")
#     return kernel


# Global kernel instance (lazy initialization)
_kernel_instance: Optional[Kernel] = None


def get_kernel() -> Kernel:
    """Get or create the global kernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = create_kernel()
    return _kernel_instance
