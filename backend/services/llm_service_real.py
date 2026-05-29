import httpx
import json
import time
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
    timeout: float = 60.0


class XingHuoLLMService:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout, connect=10.0)
        )
        self.total_tokens_used = 0

    async def chat(self, messages, system_prompt=None, temperature=None, max_tokens=None):
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": False,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_password}",
        }

        try:
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

            return {
                "content": content,
                "tokens_used": tokens_used,
                "processing_time": time.time() - start_time,
                "model": self.config.model
            }

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

    async def structured_output(self, messages, output_schema, system_prompt=None):
        schema_instruction = f"\n请严格按照以下JSON格式返回：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}\n直接返回JSON，不要其他文字。"

        full_system = f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction

        result = await self.chat(messages, system_prompt=full_system, temperature=0.3, max_tokens=2048)

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

    config = LLMConfig(
        api_password=settings.XUNFEI_API_PASSWORD,
        api_key=settings.XUNFEI_API_KEY,
        app_id=settings.XUNFEI_APP_ID,
        api_secret=settings.XUNFEI_API_SECRET,
        model=settings.LLM_MODEL
    )

    logger.info(f"[LLM] 初始化真实API服务 model={settings.LLM_MODEL} password={config.api_password[:10]}...")
    return XingHuoLLMService(config)
