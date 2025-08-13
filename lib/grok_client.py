"""
Grok Client - X.AI API wrapper with streaming and retry logic.
"""

import asyncio
import os
import time
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
import json
import logging

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
import openai

logger = logging.getLogger(__name__)


@dataclass
class GrokResponse:
    """Represents a response from Grok API."""
    content: str
    tokens_used: int
    model: str
    timestamp: float
    streaming: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "timestamp": self.timestamp,
            "streaming": self.streaming
        }


class GrokClient:
    """Client for interacting with X.AI's Grok API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-4-0709",
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize Grok client.
        
        Args:
            api_key: X.AI API key (defaults to env var XAI_API_KEY)
            model: Model to use (default: grok-4-0709)
            temperature: Sampling temperature (default: 0.7)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY not found in environment or provided")
            
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1",
        )
        
        self.total_tokens_used = 0
        
    async def ask(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = True,
        max_tokens: Optional[int] = None
    ) -> GrokResponse:
        """Send a single question to Grok.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            stream: Whether to stream the response
            max_tokens: Maximum tokens in response
            
        Returns:
            GrokResponse object with content and metadata
        """
        messages: List[ChatCompletionMessageParam] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if stream:
            return await self._stream_completion(messages, max_tokens)
        else:
            return await self._complete(messages, max_tokens)
    
    async def _complete(
        self,
        messages: List[ChatCompletionMessageParam],
        max_tokens: Optional[int] = None
    ) -> GrokResponse:
        """Get a non-streaming completion."""
        for attempt in range(self.max_retries):
            try:
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                
                content = completion.choices[0].message.content or ""
                tokens = completion.usage.total_tokens if completion.usage else 0
                self.total_tokens_used += tokens
                
                return GrokResponse(
                    content=content,
                    tokens_used=tokens,
                    model=self.model,
                    timestamp=time.time(),
                    streaming=False
                )
                
            except openai.RateLimitError as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
        raise Exception(f"Failed to get completion after {self.max_retries} attempts")
    
    async def _stream_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        max_tokens: Optional[int] = None
    ) -> GrokResponse:
        """Get a streaming completion."""
        content_parts = []
        
        for attempt in range(self.max_retries):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content_parts.append(chunk.choices[0].delta.content)
                
                content = "".join(content_parts)
                # Estimate tokens for streaming (rough approximation)
                tokens = len(content) // 4
                self.total_tokens_used += tokens
                
                return GrokResponse(
                    content=content,
                    tokens_used=tokens,
                    model=self.model,
                    timestamp=time.time(),
                    streaming=True
                )
                
            except openai.RateLimitError as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
        raise Exception(f"Failed to get streaming completion after {self.max_retries} attempts")
    
    async def stream_ask(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Stream a response token by token.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            
        Yields:
            Response chunks as they arrive
        """
        messages: List[ChatCompletionMessageParam] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        for attempt in range(self.max_retries):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
                
            except openai.RateLimitError as e:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation).
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token per 4 characters
        return len(text) // 4
    
    def get_total_tokens_used(self) -> int:
        """Get total tokens used across all requests."""
        return self.total_tokens_used
    
    def reset_token_counter(self):
        """Reset the total token counter."""
        self.total_tokens_used = 0
    
    async def ask_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> GrokResponse:
        """Send a conversation with history to Grok.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            temperature: Optional temperature override
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            
        Returns:
            GrokResponse object with content and metadata
        """
        # Convert to proper message format
        formatted_messages: List[ChatCompletionMessageParam] = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Use provided parameters or defaults
        actual_model = model or self.model
        actual_temp = temperature if temperature is not None else self.temperature
        
        # Temporarily update instance values
        old_model = self.model
        old_temp = self.temperature
        self.model = actual_model
        self.temperature = actual_temp
        
        try:
            if stream:
                response = await self._stream_completion(formatted_messages, max_tokens)
            else:
                response = await self._complete(formatted_messages, max_tokens)
            return response
        finally:
            # Restore original values
            self.model = old_model
            self.temperature = old_temp