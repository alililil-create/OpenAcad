import asyncio

try:
    from openai import AsyncOpenAI
except ImportError:
    print("pip install openai")
    exit(1)

TEST_KEYS = [
    ("旧UUID格式", "201de072-63c6-4a9a-815a-b96fba3ca0f1"),
    ("AccessKeyId", "AKLTOTFkMDE3MWE4YWExNDNlN2JjNjk2NzBhZjA1NWNlNzY"),
    ("SecretAccessKey原始", "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="),
    ("SK解码后", "YzBiZmVmZWYwNzMxNDk4Mjg3N2Y5MTQxODlkOWE2ZGY"),
    ("SK双重解码", "c0bfefef07314982877f914189d9a6df"),
]

BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "ep-20260601002955-t6bkd"

async def test_one(name, api_key):
    client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "OK"}],
            max_tokens=5,
        )
        print(f"  ✅ {name}: 成功! 回复={resp.choices[0].message.content}")
        return True
    except Exception as e:
        err = str(e)[:100]
        print(f"  ❌ {name}: {err}")
        return False

async def main():
    print("=" * 60)
    print("批量测试所有可能的 Key 格式")
    print("=" * 60)
    
    for name, key in TEST_KEYS:
        print(f"\n[{name}] Key: {key[:25]}...")
        await test_one(name, key)

if __name__ == "__main__":
    asyncio.run(main())
