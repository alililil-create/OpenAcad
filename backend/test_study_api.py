import sys
sys.path.insert(0, '.')
import asyncio
from backend.routers.study import generate_study_materials

async def test_study():
    print("="*80)
    print("测试 study API")
    print("="*80)

    # 测试用 user_id=4, chapter_id=programming
    user_id = 4
    chapter_id = "programming"

    print(f"\n[Test] 测试 user_id={user_id} chapter_id={chapter_id}\n")
    response = await generate_study_materials(user_id, chapter_id)
    
    print(f"[Result] 响应类型: {type(response)}")
    print(f"[Result] 媒体类型: {response.media_type}")
    print(f"\n现在去浏览器访问 http://127.0.0.1:8000/api/study/generate/{user_id}/{chapter_id}")

if __name__ == "__main__":
    asyncio.run(test_study())
