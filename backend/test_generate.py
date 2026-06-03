import asyncio
import json
import urllib.request

API_BASE = "http://127.0.0.1:8000"
USER_ID = 4
CHAPTER_ID = "math_foundation"

async def test():
    url = f"{API_BASE}/api/study/generate/{USER_ID}/{CHAPTER_ID}"
    print(f"=" * 70)
    print(f"测试文档+题库生成")
    print(f"URL: {url}")
    print(f"=" * 70)

    req = urllib.request.Request(url)
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"\n[HTTP] Status: {resp.status}")
            print(f"[HTTP] Content-Type: {resp.headers.get('Content-Type')}")
            
            buffer = b""
            for chunk in iter(lambda: resp.read(4096), b""):
                buffer += chunk
                text = buffer.decode("utf-8", errors="replace")
                
                lines = text.split("\n\n")
                buffer = b""
                if text.endswith("\n"):
                    pass
                else:
                    buffer = lines[-1].encode()
                    lines = lines[:-1]
                    
                for line in lines:
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[6:])
                        etype = event.get("type", "?")
                        
                        if etype == "agent_start":
                            print(f"\n▶️  开始: {event.get('agent')} - {event.get('name', '')} (Stage {event.get('stage')})")
                        
                        elif etype == "agent_complete":
                            print(f"✅ 完成: {event.get('agent')} (Stage {event.get('stage')})")
                            
                        elif etype == "agent_content":
                            agent = event.get("agent", "")
                            parts = event.get("content_parts", {})
                            content = event.get("content", "")
                            
                            if parts:
                                for key, val in parts.items():
                                    v = str(val)
                                    if len(v) > 200:
                                        v = v[:200] + f"... ({len(v)} chars)"
                                    print(f"   📦 [{key}] {v}")
                            elif content:
                                c = str(content)[:150]
                                print(f"   💬 {c}")
                                
                        elif etype == "error":
                            print(f"\n❌ 错误: {event.get('message', 'unknown')}")
                            
                        elif etype == "done":
                            print(f"\n{'='*50}")
                            print(f"🎉 全部完成! 共 {event.get('total_stages', '?')} 阶段")
                            print(f"{'='*50}")
                    except json.JSONDecodeError as e:
                        print(f"  [parse error] {e}: {line[:100]}")

        print("\n[OK] SSE流正常结束")
        
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        print(f"\n❌ HTTP Error: {e.code} {e.reason}")
        print(f"Body: {body}")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        CHAPTER_ID = sys.argv[1]
    if len(sys.argv) > 2:
        USER_ID = int(sys.argv[2])
    asyncio.run(test())
