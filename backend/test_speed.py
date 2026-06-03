import asyncio
from openai import AsyncOpenAI
import time

API_KEY = "201de072-63c6-4a9a-815a-b96fba3ca0f1"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "ep-20260601002955-t6bkd"

async def test():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    print("测试1: 短回复 (10 tokens)")
    t0 = time.time()
    r1 = await client.chat.completions.create(
        model=MODEL, messages=[{"role":"user","content":"说OK"}], max_tokens=10
    )
    print(f"  耗时: {time.time()-t0:.1f}s | 回复: {r1.choices[0].message.content}")
    
    print("\n测试2: 中等回复 (500 tokens)")
    t0 = time.time()
    r2 = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":"用3句话解释什么是线性代数"}],
        max_tokens=500
    )
    print(f"  耗时: {time.time()-t0:.1f}s | 字数: {len(r2.choices[0].message.content)}")
    
    print("\n测试3: 长回复 (2000 tokens) - 模拟文档生成")
    t0 = time.time()
    r3 = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":"写一篇关于线性代数的教程，包含概念、公式、代码示例，约1500字"}],
        max_tokens=2000
    )
    elapsed = time.time() - t0
    content = r3.choices[0].message.content
    print(f"  耗时: {elapsed:.1f}s | 字数: {len(content)}")
    print(f"  前100字: {content[:100]}...")

if __name__ == "__main__":
    asyncio.run(test())
