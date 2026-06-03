import asyncio

try:
    from openai import AsyncOpenAI
except ImportError:
    print("需要安装: pip install openai")
    exit(1)

API_KEY = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "ep-20260601002955-t6bkd"

async def test():
    print("=" * 60)
    print("测试 OpenAI SDK 调用火山方舟")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Model:    {MODEL}")
    print(f"API Key:  {API_KEY[:20]}...")
    
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "回复OK两个字"}],
            max_tokens=10,
        )
        
        content = resp.choices[0].message.content
        print(f"\n✅✅✅ 成功! 回复: {content}")
        print(f"模型: {resp.model}")
        print(f"Token: {resp.usage.total_tokens if resp.usage else 'N/A'}")
        return True
        
    except Exception as e:
        print(f"\n❌ 失败: {type(e).__name__}: {e}")
        
        # 尝试带 /chat/completions 后缀的 base_url
        print("\n--- 尝试 base_url 带 /chat/completions ---")
        client2 = AsyncOpenAI(
            api_key=API_KEY,
            base_url=BASE_URL + "/chat/completions",
        )
        try:
            resp2 = await client2.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "回复OK"}],
                max_tokens=10,
            )
            content2 = resp2.choices[0].message.content
            print(f"\n✅ 成功(方式2)! 回复: {content2}")
            return True
        except Exception as e2:
            print(f"❌ 方式2也失败: {e2}")
        return False

if __name__ == "__main__":
    asyncio.run(test())
