import asyncio
import httpx
import hashlib
import hmac
import json
from datetime import datetime, timezone

AK = "AKLTOTFkMDE3MWE4YWExNDNlN2JjNjk2NzBhZjA1NWNlNzY"
SK = "WXpCaVptVm1aV1l3TnpNeE5EazRNamczTjJZNU1UUXhPRGxrT1dFMlpHWQ=="
MODEL = "ep-20260601002955-t6bkd"
HOST = "ark.cn-beijing.volces.com"

def sign_request(method: str, uri: str, body: str = "") -> dict:
    now = datetime.now(timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = x_date[:8]
    service = "ark"
    credential_scope = f"{date_stamp}/{service}/request"

    hashed_body = hashlib.sha256(body.encode("utf-8")).hexdigest()

    canonical_headers = f"host:{HOST}\nx-authorization-date:{x_date}\n"
    signed_headers = "host;x-authorization-date"

    canonical_request = (
        f"{method}\n{uri}\n\n{canonical_headers}\n{signed_headers}\n{hashed_body}"
    )
    canonical_hash = hashlib.sha256(canonical_request.encode()).hexdigest()

    string_to_sign = f"VOLC3-HMAC-SHA256\n{x_date}\n{credential_scope}\n{canonical_hash}"

    k_date = hmac.new(f"VOLC3{SK}".encode(), date_stamp.encode(), hashlib.sha256).digest()
    k_service = hmac.new(k_date, service.encode(), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"VOLC3-HMAC-SHA256 Credential={AK}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "Authorization": authorization,
        "X-Authorization-Date": x_date,
        "Content-Type": "application/json",
    }

async def test():
    print("=" * 60)
    print("测试 VOLC3-HMAC-SHA256 签名认证")
    print("=" * 60)

    url = f"https://{HOST}{MODEL}" if MODEL.startswith("ep") else f"https://{HOST}/api/v3/chat/completions"
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "回复OK"}],
        "max_tokens": 10
    }
    body_str = json.dumps(payload, ensure_ascii=False)

    headers = sign_request("POST", "/api/v3/chat/completions", body_str)
    
    print(f"\n[URL] POST https://{HOST}/api/v3/chat/completions")
    print(f"[Model] {MODEL}")
    print(f"[Auth] {headers['Authorization'][:80]}...")
    print(f"[Date] {headers['X-Authorization-Date']}")

    client = httpx.AsyncClient(timeout=30)
    
    try:
        resp = await client.post(
            f"https://{HOST}/api/v3/chat/completions",
            headers=headers,
            content=body_str
        )
        print(f"\n[Status] {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ 成功! 回复: {content}")
        else:
            print(f"❌ 失败! Body: {resp.text[:400]}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    asyncio.run(test())
