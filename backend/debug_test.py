#!/usr/bin/env python
import asyncio, httpx, json, sys
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_PASSWORD = os.getenv("XUNFEI_API_PASSWORD", "")
URL = "https://spark-api-open.xf-yun.com/v2/chat/completions"

async def main():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_PASSWORD}",
    }
    
    # 测试 spark-x 并打印完整响应
    for model in ["spark-x", "spark-X"]:
        print(f"\n{'='*50}")
        print(f"测试: {model}")
        print(f"{'='*50}")
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 20,
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(URL, headers=headers, json=payload)
            print(f"状态码: {r.status_code}")
            print(f"响应体:\n{json.dumps(r.json(), ensure_ascii=False, indent=2)}")

asyncio.run(main())
