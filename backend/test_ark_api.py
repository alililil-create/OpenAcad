import asyncio
import httpx
import json

API_KEY = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="
MODEL = "ep-20260601002955-t6bkd"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

async def test():
    print("=" * 60)
    print("直接测试火山方舟 API")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Model:    {MODEL}")
    print(f"API Key:  {API_KEY[:15]}...")
    
    client = httpx.AsyncClient(timeout=30)
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "你好，请回复OK"}],
        "stream": False,
        "max_tokens": 10
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    
    url = f"{BASE_URL}/chat/completions"
    print(f"\n[测试1] POST {url}")
    print(f"[Header] Authorization: Bearer {API_KEY[:15]}...")
    
    try:
        resp = await client.post(url, headers=headers, json=payload)
        print(f"\n[响应] Status: {resp.status_code}")
        print(f"[响应] Headers: {dict(resp.headers)}")
        
        body = resp.text
        if len(body) > 500:
            body = body[:500] + f"... ({len(body)} chars total)"
        print(f"[响应] Body:\n{body}")
        
    except Exception as e:
        print(f"\n[错误] {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
