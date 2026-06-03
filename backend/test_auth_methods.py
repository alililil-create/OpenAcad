import asyncio
import httpx
import json

API_KEY = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="
AK_ID = "AKLTOTFkMDE3MWE4YWExNDNlN2JjNjk2NzBhZjA1NWNlNzY"
MODEL = "ep-20260601002955-t6bkd"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

async def test_auth_method(name, headers):
    client = httpx.AsyncClient(timeout=30)
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "回复OK"}],
        "max_tokens": 10
    }
    url = f"{BASE_URL}/chat/completions"
    
    print(f"\n{'='*50}")
    print(f"[测试] {name}")
    print(f"[Header] {json.dumps(headers, indent=2)}")
    
    try:
        resp = await client.post(url, headers=headers, json=payload)
        body = resp.text[:300]
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\n✅ 成功! Status: {resp.status_code}")
            print(f"   回复: {content}")
            return True
        else:
            print(f"\n❌ 失败! Status: {resp.status_code}")
            print(f"   Body: {body}")
            return False
            
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False

async def main():
    print("=" * 60)
    print("测试不同认证方式")
    print("=" * 60)

    results = []
    
    # 方式1: Authorization: Bearer SK (当前方式)
    results.append(await test_auth_method(
        "方式1: Bearer + SecretAccessKey",
        {"Content-Type": "application/json",
         "Authorization": f"Bearer {API_KEY}"}
    ))
    
    # 方式2: X-Api-Key header (OpenAI兼容变体)
    results.append(await test_auth_method(
        "方式2: X-Api-Key + SecretAccessKey",
        {"Content-Type": "application/json",
         "X-Api-Key": API_KEY}
    ))
    
    # 方式3: Authorization: Bearer AK (Access Key ID)
    results.append(await test_auth_method(
        "方式3: Bearer + AccessKeyId",
        {"Content-Type": "application/json",
         "Authorization": f"Bearer {AK_ID}"}
    ))
    
    # 方式4: X-Api-Key + AK
    results.append(await test_auth_method(
        "方式4: X-Api-Key + AccessKeyId",
        {"Content-Type": "application/json",
         "X-Api-Key": AK_ID}
    ))
    
    # 方式5: /responses 端点 (官方示例用的端点)
    client = httpx.AsyncClient(timeout=30)
    url2 = f"{BASE_URL}/responses"
    payload2 = {
        "model": MODEL,
        "input": [{"role": "user", "content": "回复OK"}],
    }
    print(f"\n{'='*50}")
    print("[测试] 方式5: /responses端点 + Bearer+SK")
    try:
        resp = await client.post(url2,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {API_KEY}"},
            json=payload2)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:300]}")
        if resp.status_code == 200:
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"异常: {e}")
        results.append(False)
    
    print("\n" + "=" * 60)
    if any(results):
        print("✅ 至少有一种方式成功!")
    else:
        print("❌ 所有方式都失败，可能需要HMAC签名")

if __name__ == "__main__":
    asyncio.run(main())
