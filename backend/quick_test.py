#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试不同模型名称"""

import asyncio
import httpx
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

sys.path.insert(0, str(Path(__file__).parent))
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

API_PASSWORD = os.getenv("XUNFEI_API_PASSWORD", "")
URL = "https://spark-api-open.xf-yun.com/v2/chat/completions"

print(f"\n{'='*60}")
print(f"🔧 API Password: {API_PASSWORD[:15]}...")
print(f"🔧 URL: {URL}")
print(f"{'='*60}\n")

# 根据你的截图，Spark X2/X1.5 可能的模型名
MODELS = [
    "spark-x",       # 最有可能！截图显示 "Spark X"
    "X2",
    "x2",
    "X1.5",
    "x1.5",
    "spark-x2",
    "spark-X2",
    "generalv3.5",   # Max
    "generalv3",     # Pro
    "lite",
    "4.0Ultra",
]

async def test_one(model):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_PASSWORD}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 20,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(URL, headers=headers, json=payload)
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices",[{}])[0].get("message",{}).get("content","")
                print(f"  ✅ {model:20s} → {content[:60]}")
                return True, model
            else:
                err = ""
                try:
                    err = r.json().get("message","")[:50]
                except:
                    pass
                print(f"  ❌ {model:20s} → [{r.status_code}] {err}")
                return False, None
    except Exception as e:
        print(f"  ❌ {model:20s} → 异常: {str(e)[:40]}")
        return False, None

async def main():
    print("测试模型名称...\n")
    ok = []
    for m in MODELS:
        success, name = await test_one(m)
        if success:
            ok.append(name)
        await asyncio.sleep(0.3)
    
    if ok:
        print(f"\n🎉 成功的模型: {ok}")
        print(f"💡 在 .env 中设置 LLM_MODEL={ok[0]}")
    else:
        print("\n⚠️ 都失败了，请确认控制台中的接口地址")

asyncio.run(main())
