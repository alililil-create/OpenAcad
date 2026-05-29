#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Spark X2 API 连接测试脚本

使用方法：
    cd backend
    python test_spark_x2.py

功能：
    1. 测试API连接
    2. 测试非流式对话
    3. 测试结构化输出（画像提取）
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_basic_connection():
    """测试1：基础连接"""
    print("\n" + "="*60)
    print("🧪 测试1：基础连接测试")
    print("="*60)

    try:
        from services.llm_service import get_llm_service, test_connection

        result = await test_connection()
        if result:
            print("✅ 基础连接成功！")
            return True
        else:
            print("❌ 基础连接失败")
            return False

    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")
        return False


async def test_chat():
    """测试2：多轮对话"""
    print("\n" + "="*60)
    print("🧪 测试2：多轮对话测试")
    print("="*60)

    try:
        from services.llm_service import get_llm_service

        llm = await get_llm_service()

        # 模拟学生对话
        messages = [
            {"role": "user", "content": "你好，我是计算机专业的大二学生"}
        ]

        result = await llm.chat(
            messages=messages,
            system_prompt="你是一个友好的AI学习助手，请用简短的话回复。"
        )

        print(f"\n📝 用户输入: {messages[0]['content']}")
        print(f"🤖 AI回复: {result['content'][:200]}...")
        print(f"⏱️ 耗时: {result['processing_time']:.2f}秒")
        print(f"📊 Token消耗: {result['tokens_used']}")

        print("\n✅ 对话测试成功！")
        return True

    except Exception as e:
        print(f"❌ 对话测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_profile_extraction():
    """测试3：画像提取（核心功能）"""
    print("\n" + "="*60)
    print("🧪 测试3：学生画像提取测试（核心功能）")
    print("="*60)

    try:
        from services.llm_service import get_llm_service

        llm = await get_llm_service()

        # 模拟学生自我介绍
        user_input = """
        我是计算机科学与技术专业的大二学生。
        我的数学基础还可以，高等数学考了80分。
        我学过Python编程，能写一些简单的数据处理代码。
        对于机器学习，我只听说过一些概念，比如神经网络、深度学习这些词。
        我想学习机器学习是为了以后能做人工智能相关的工作。
        我每周大概能拿出15个小时来学习。
        我比较擅长逻辑思维，但数学推导比较薄弱。
        我希望理论与实践结合的学习方式。
        """

        # 定义画像Schema
        profile_schema = {
            "major": "专业名称",
            "grade_level": "年级",
            "math_foundation": 3,
            "programming_exp": 3,
            "ml_knowledge": 2,
            "learning_style": "学习风格",
            "learning_goal": "学习目标",
            "weak_points": ["薄弱点"],
            "weekly_hours": 10,
            "interests": ["兴趣方向"],
            "preferred_language": "Python"
        }

        print(f"\n👤 学生输入:\n{user_input[:150]}...")

        # 调用结构化输出
        result = await llm.structured_output(
            messages=[{"role": "user", "content": user_input}],
            output_schema=profile_schema,
            system_prompt="你是教育心理学专家，擅长通过学生的自我介绍分析学习特征。"
        )

        print("\n🎯 提取的画像数据:")
        print("-" * 40)
        for key, value in result.items():
            if key != "_meta":
                print(f"  • {key}: {value}")
        print("-" * 40)

        meta = result.get("_meta", {})
        print(f"\n📊 元数据:")
        print(f"  • Token消耗: {meta.get('tokens_used', 'N/A')}")
        print(f"  • 使用模型: {meta.get('model', 'N/A')}")

        # 验证关键字段
        required_fields = ["major", "grade_level", "math_foundation", "learning_goal"]
        missing_fields = [f for f in required_fields if f not in result or not result[f]]

        if missing_fields:
            print(f"\n⚠️ 缺少字段: {missing_fields}")
            return False
        else:
            print("\n✅ 画像提取成功！所有关键字段都已获取。")
            return True

    except Exception as e:
        print(f"❌ 画像提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_streaming():
    """测试4：流式输出"""
    print("\n" + "="*60)
    print("🧪 测试4：流式输出测试")
    print("="*60)

    try:
        from services.llm_service import get_llm_service

        llm = await get_llm_service()

        print("\n🔄 开始流式接收（模拟打字机效果）...\n")

        full_text = ""
        char_count = 0

        async for chunk in llm.chat_stream(
            messages=[{"role": "user", "content": "请用三句话介绍机器学习"}],
            system_prompt="你是一个简洁的AI助手。"
        ):
            print(chunk, end='', flush=True)  # 实时打印
            full_text += chunk
            char_count += 1

            # 每50个字符换行一次避免太长
            if char_count % 50 == 0:
                print()  # 换行

        print("\n\n✅ 流式输出完成！")
        print(f"📏 总字符数: {len(full_text)}")

        return True

    except Exception as e:
        print(f"\n❌ 流式输出失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("🔥 讯飞 Spark X2 API 完整测试套件")
    print("🚀"*30)

    results = {
        "基础连接": await test_basic_connection(),
        "多轮对话": await test_chat(),
        "画像提取": await test_profile_extraction(),
        "流式输出": await test_streaming(),
    }

    # 汇总结果
    print("\n\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}  {test_name}")

    print("-"*60)
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 恭喜！所有测试通过！你的Spark X2配置完全正常。")
        print("\n下一步操作:")
        print("  1. 启动后端服务: cd backend && python app.py")
        print("  2. 启动前端服务: cd bei && python -m http.server 3000")
        print("  3. 打开浏览器访问: http://localhost:3000")
        print("  4. 注册账号 → 进入画像页面体验7个Agent协作！")
    else:
        print("\n⚠️ 部分测试未通过，请检查：")
        print("  1. API密钥是否正确复制到 .env 文件")
        print("  2. 网络连接是否正常")
        print("  3. 讯飞API额度是否充足")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
