#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 尝试多个模型名称找到正确的
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 从配置加载
from dotenv import load_dotenv
import os

# 加载 .env 文件
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

API_PASSWORD = os.getenv("XUNFEI_API_PASSWORD", "")
APP_ID = os.getenv("XUNFEI_APP_ID", "")

print(f"\n{'='*60}")
print(f"🔧 API Password: {API_PASSWORD[:15]}...")
print(f"🔧 App ID: {APP_ID}")
print(f"{'='*60}\n")

# 要测试的模型列表（按可能性排序）
MODELS_TO_TEST = [
    ("generalv3.5", "Spark Max (旗舰)"),
    ("spark-x", "Spark X (新版?)"),
    ("X2", "Spark X2 (直接用)"),
    ("generalv3", "Spark Pro (专业)"),
    ("lite", "Spark Lite (免费)"),
    ("4.0Ultra", "Spark 4.0 Ultra (最强)"),
    ("max-32k", "Spark Max-32K"),
]

async def test_model(model_name, model_desc):
    """测试单个模型"""
    url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_PASSWORD}",
    }
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 20,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"✅ {model_desc:25s} | model={model_name:15s} | 回复: {content[:50]}...")
                return True, model_name, content
            else:
                error_msg = ""
                try:
                    error_body = response.json()
                    error_msg = error_body.get("message", "")[:60]
                except:
                    error_msg = response.text[:60]
                
                print(f"❌ {model_desc:25s} | model={model_name:15s} | 错误[{response.status_code}]: {error_msg}")
                return False, model_name, None
                
    except Exception as e:
        print(f"❌ {model_desc:25s} | model={model_name:15s} | 异常: {str(e)[:50]}")
        return False, model_name, None


async def main():
    print("开始测试不同模型名称...\n")
    
    success_models = []
    
    for model_name, model_desc in MODELS_TO_TEST:
        success, name, content = await test_model(model_name, model_desc)
        if success:
            success_models.append((name, model_desc, content))
        
        # 稍微延迟避免请求过快
        await asyncio.sleep(0.5)
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    
    if success_models:
        print(f"\n🎉 成功的模型 ({len(success_models)}个):")
        for name, desc, content in success_models:
            print(f"  ✅ {desc}")
            print(f"     model参数: {name}")
            print(f"     测试回复: {content[:80]}...\n")
        
        # 使用第一个成功的模型更新配置
        best_model = success_models[0][0]
        print(f"💡 建议：在 .env 中设置 LLM_MODEL={best_model}")
    else:
        print("\n⚠️ 所有模型都失败了！可能的原因:")
        print("  1. 该 AppID 未开通任何模型的权限")
        print("  2. APIPassword 不正确")
        print("  3. 免费额度已用完")
        print("\n👉 请访问 https://console.xfyun.cn/services/cbm 检查:")
        print("  • 是否有可用额度")
        print("  • 是否开通了相应模型服务")


if __name__ == "__main__":
    asyncio.run(main())
