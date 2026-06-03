import httpx
import json
import time
import hashlib
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _make_cache_payload(messages, system_prompt, temperature, max_tokens):
    """根据 LLM 调用参数生成缓存 key 的输入指纹"""
    payload = {
        "messages": messages,
        "system": system_prompt or "",
        "temp": temperature,
        "max": max_tokens
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


@dataclass
class LLMConfig:
    api_password: str = ""
    api_key: str = ""
    app_id: str = ""
    api_secret: str = ""
    model: str = "spark-x"
    base_url: str = "https://spark-api-open.xf-yun.com/v2/chat/completions"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 180.0


class XingHuoLLMService:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout, connect=10.0)
        )
        self.total_tokens_used = 0

    async def _write_cache(self, cache_agent, cache_chapter, cache_stage, cache_profile_hash, content_hash, content, cache_user_id=0):
        from services.cache_service import CacheService
        try:
            combined = hashlib.md5(f"{cache_profile_hash}:{content_hash}".encode()).hexdigest()[:12]
            await CacheService.set_llm_cache(cache_agent, cache_chapter, cache_stage, content, combined, user_id=cache_user_id)
        except Exception as e:
            logger.warning(f"[LLM] 缓存写入失败(非阻塞): {e}")

    async def chat(self, messages, system_prompt=None, temperature=None, max_tokens=None, cache_agent=None, cache_chapter=None, cache_stage=None, cache_profile_hash="", cache_user_id=0, use_cache=True, write_cache=True):
        from services.cache_service import CacheService

        effective_max = max_tokens or self.config.max_tokens
        full_payload_for_hash = {
            "messages": messages,
            "system": system_prompt or "",
            "temp": temperature,
            "max": effective_max
        }
        content_hash = _make_cache_payload(messages, system_prompt, temperature, effective_max)
        combined_hash = hashlib.md5(f"{cache_profile_hash}:{content_hash}".encode()).hexdigest()[:12]
        if use_cache and cache_agent and cache_chapter and cache_stage:
            cached = await CacheService.get_llm_cache(cache_agent, cache_chapter, cache_stage, combined_hash, user_id=cache_user_id)
            if cached:
                logger.info(f"[LLM] cache hit: u{cache_user_id}/{cache_agent}/{cache_chapter}/{cache_stage}")
                return {
                    "content": cached["content"],
                    "tokens_used": 0,
                    "processing_time": 0.001,
                    "model": self.config.model,
                    "_from_cache": True
                }

        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": False,
            "temperature": temperature or self.config.temperature,
            "max_tokens": effective_max
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_password}",
        }

        try:
            start_time = time.time()
            logger.info(f"[LLM] request: model={self.config.model}, user_id={cache_user_id}, messages={len(full_messages)}, max_tokens={effective_max}")
            response = await self.client.post(self.config.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)
            else:
                content = str(result)
                tokens_used = 0

            elapsed = time.time() - start_time
            logger.info(f"[LLM] response: {elapsed:.2f}s, tokens={tokens_used}, content_len={len(content)}")

            if use_cache and write_cache and cache_agent and cache_chapter and cache_stage:
                await self._write_cache(cache_agent, cache_chapter, cache_stage, cache_profile_hash, content_hash, content, cache_user_id=cache_user_id)

            return {
                "content": content,
                "tokens_used": tokens_used,
                "processing_time": elapsed,
                "model": self.config.model
            }

        except httpx.TimeoutException:
            logger.error(f"[LLM] chat timeout after {self.config.timeout}s")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"[LLM] HTTP {e.response.status_code}: {e.response.text[:300]}")
            raise
        except Exception as e:
            logger.error(f"[LLM] chat failed: {str(e)}")
            raise

    async def chat_stream(self, messages, system_prompt=None):
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": True,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_password}",
            "Accept": "text/event-stream"
        }

        try:
            async with self.client.stream("POST", self.config.base_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices", [])
                            if len(choices) > 0:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                                    self.total_tokens_used += len(content)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"[LLM] stream failed: {str(e)}")
            raise

    async def structured_output(self, messages, output_schema, system_prompt=None, cache_user_id=0):
        schema_instruction = f"\n请严格按照以下JSON格式返回：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}\n直接返回JSON，不要其他文字。"

        full_system = f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction

        result = await self.chat(messages, system_prompt=full_system, temperature=0.3, max_tokens=2048, cache_user_id=cache_user_id, use_cache=False, write_cache=False)

        try:
            content = result["content"].strip()
            for prefix in ["```json", "```JSON", "```"]:
                if content.startswith(prefix):
                    content = content[len(prefix):]
                    break
            for suffix in ["```"]:
                if content.endswith(suffix):
                    content = content[:-len(suffix)]
            content = content.strip()
            if len(content) >= 2 and ((content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'"))):
                content = content[1:-1]
            parsed = json.loads(content)
            return {**parsed, "_meta": {"tokens_used": result["tokens_used"]}}
        except json.JSONDecodeError as e:
            raise Exception(f"JSON parse failed: {e}\nRaw: {result['content'][:500]}")

    async def simple_chat(self, message: str) -> str:
        result = await self.chat([{"role": "user", "content": message}])
        return result["content"]

    async def close(self):
        await self.client.aclose()


class DeepSeekLLMService:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout, connect=10.0)
        )
        self.total_tokens_used = 0

    async def _write_cache(self, cache_agent, cache_chapter, cache_stage, cache_profile_hash, content_hash, content, cache_user_id=0):
        from services.cache_service import CacheService
        try:
            combined = hashlib.md5(f"{cache_profile_hash}:{content_hash}".encode()).hexdigest()[:12]
            await CacheService.set_llm_cache(cache_agent, cache_chapter, cache_stage, content, combined, user_id=cache_user_id)
        except Exception as e:
            logger.warning(f"[DeepSeek] 缓存写入失败(非阻塞): {e}")

    async def chat(self, messages, system_prompt=None, temperature=None, max_tokens=None, cache_agent=None, cache_chapter=None, cache_stage=None, cache_profile_hash="", cache_user_id=0, use_cache=True, write_cache=True):
        from services.cache_service import CacheService

        effective_max = max_tokens or self.config.max_tokens
        content_hash = _make_cache_payload(messages, system_prompt, temperature, effective_max)
        combined_hash = hashlib.md5(f"{cache_profile_hash}:{content_hash}".encode()).hexdigest()[:12]
        if use_cache and cache_agent and cache_chapter and cache_stage:
            cached = await CacheService.get_llm_cache(cache_agent, cache_chapter, cache_stage, combined_hash, user_id=cache_user_id)
            if cached:
                logger.info(f"[DeepSeek] cache hit: u{cache_user_id}/{cache_agent}/{cache_chapter}/{cache_stage}")
                return {
                    "content": cached["content"],
                    "tokens_used": 0,
                    "processing_time": 0.001,
                    "model": self.config.model,
                    "_from_cache": True
                }

        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": False,
            "temperature": temperature or self.config.temperature,
            "max_tokens": effective_max
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            logger.info(f"[DeepSeek] 请求 URL: {self.config.base_url}")
            logger.info(f"[DeepSeek] 请求 model: {self.config.model}, user_id={cache_user_id}")
            logger.info(f"[DeepSeek] 请求 API Key: {self.config.api_key[:10]}...")
            start_time = time.time()
            response = await self.client.post(self.config.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)
            else:
                content = str(result)
                tokens_used = 0

            elapsed = time.time() - start_time
            logger.info(f"[DeepSeek] response: {elapsed:.2f}s, tokens={tokens_used}, content_len={len(content)}")

            if use_cache and write_cache and cache_agent and cache_chapter and cache_stage:
                await self._write_cache(cache_agent, cache_chapter, cache_stage, cache_profile_hash, content_hash, content, cache_user_id=cache_user_id)

            return {
                "content": content,
                "tokens_used": tokens_used,
                "processing_time": elapsed,
                "model": self.config.model
            }

        except httpx.TimeoutException:
            logger.error(f"[DeepSeek] chat timeout after {self.config.timeout}s")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek] HTTP {e.response.status_code}: {e.response.text[:300]}")
            raise
        except Exception as e:
            logger.error(f"[DeepSeek] chat failed: {str(e)}")
            raise

    async def chat_stream(self, messages, system_prompt=None):
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": True,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "text/event-stream"
        }

        try:
            async with self.client.stream("POST", self.config.base_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices", [])
                            if len(choices) > 0:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                                    self.total_tokens_used += len(content)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"[DeepSeek] stream failed: {str(e)}")
            raise

    async def structured_output(self, messages, output_schema, system_prompt=None, cache_user_id=0):
        schema_instruction = f"\n请严格按照以下JSON格式返回：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}\n直接返回JSON，不要其他文字。"

        full_system = f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction

        result = await self.chat(messages, system_prompt=full_system, temperature=0.3, max_tokens=2048, cache_user_id=cache_user_id, use_cache=False, write_cache=False)

        try:
            content = result["content"].strip()
            for prefix in ["```json", "```JSON", "```"]:
                if content.startswith(prefix):
                    content = content[len(prefix):]
                    break
            for suffix in ["```"]:
                if content.endswith(suffix):
                    content = content[:-len(suffix)]
            content = content.strip()
            if len(content) >= 2 and ((content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'"))):
                content = content[1:-1]
            parsed = json.loads(content)
            return {**parsed, "_meta": {"tokens_used": result["tokens_used"]}}
        except json.JSONDecodeError as e:
            raise Exception(f"JSON parse failed: {e}\nRaw: {result['content'][:500]}")

    async def simple_chat(self, message: str) -> str:
        result = await self.chat([{"role": "user", "content": message}])
        return result["content"]

    async def close(self):
        await self.client.aclose()


async def get_llm_service():
    from config import settings

    provider = settings.LLM_PROVIDER.lower()

    if provider == "deepseek":
        config = LLMConfig(
            api_key=settings.DEEPSEEK_API_KEY,
            model=settings.DEEPSEEK_MODEL,
            base_url=f"{settings.DEEPSEEK_BASE_URL}/chat/completions"
        )
        logger.info(f"[LLM] 初始化 DeepSeek 服务 model={settings.DEEPSEEK_MODEL} base_url={settings.DEEPSEEK_BASE_URL}")
        logger.info(f"[LLM] 完整请求 URL: {config.base_url}")
        return DeepSeekLLMService(config)

    config = LLMConfig(
        api_password=settings.XUNFEI_API_PASSWORD,
        api_key=settings.XUNFEI_API_KEY,
        app_id=settings.XUNFEI_APP_ID,
        api_secret=settings.XUNFEI_API_SECRET,
        model=settings.LLM_MODEL
    )

    logger.info(f"[LLM] 初始化讯飞星火服务 model={settings.LLM_MODEL} password={config.api_password[:10]}...")
    return XingHuoLLMService(config)
