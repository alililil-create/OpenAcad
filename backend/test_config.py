import sys
sys.path.insert(0, '.')
from config import settings

print("="*60)
print("[测试] 配置加载检查")
print("="*60)
print(f"LLM_PROVIDER:        {settings.LLM_PROVIDER}")
print(f"LLM_MODEL:           {settings.LLM_MODEL}")
print(f"DEEPSEEK_BASE_URL:   {settings.DEEPSEEK_BASE_URL}")
print(f"DEEPSEEK_MODEL:      {settings.DEEPSEEK_MODEL}")
print(f"DEEPSEEK_API_KEY:    {settings.DEEPSEEK_API_KEY[:10]}...")
print("="*60)
