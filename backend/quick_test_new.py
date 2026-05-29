#!/usr/bin/env python
"""快速测试新API凭证"""
import asyncio
import httpx
import json
from pathlib import Path
from dotenv import load_dotenv
import os, sys

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_PASSWORD = os.getenv("XUNFEI_API_PASSWORD", "")
URL = "https://spark-api-open.xf-yun.com/v2/chat/completions"

print(f"\n{'='*60}")
print(f"🔧 API Password: {API_PASSWORD[:15]}...")
print(f"🔧 URL: {URL}")
print(f"{'='*60}\n")

async def main():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_PASSWORD}",
    }
    payload = {
        "model": "spark-x",
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 50,
    }
    
    print("🚀 发送测试请求...\n")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(URL, headers=headers, json=payload)
        print(f"状态码: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            content = data.get("choices",[{}])[0].get("message",{}).get("content","")
            print(f"✅ 成功！AI回复: {content[:100]}")
            return True
        else:
            try:
                err = r.json().get("message","")[:200]
            except:
                err = r.text[:200]
            print(f"❌ 失败: [{r.status_code}] {err}")
            return False

asyncio.run(main())
