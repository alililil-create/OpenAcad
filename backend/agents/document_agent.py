from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class DocumentAgent:
    """根据知识点和学生画像生成个性化讲解文档(Markdown)"""

    AGENT_NAME = "document_agent"

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        start_time = time.time()

        try:
            logger.info(f"[{self.AGENT_NAME}] 开始处理...")

            input_data = self._extract_input(state)
            output_data = await self._process(input_data)
            result = self._build_result(output_data)

            execution_time = time.time() - start_time
            log_entry = {
                "agent_name": self.AGENT_NAME,
                "start_time": start_time,
                "end_time": time.time(),
                "status": "success",
                "input_summary": str(input_data)[:100],
                "output_preview": str(result)[:200],
                "processing_time": execution_time
            }

            logger.info(f"[{self.AGENT_NAME}] 处理完成，耗时 {execution_time:.2f}s")

            return {
                **result,
                "current_agent": self.AGENT_NAME,
                "execution_log": state.get("execution_log", []) + [log_entry],
                "processing_time": {**(state.get("processing_time", {})),
                                   self.AGENT_NAME: execution_time}
            }

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] 处理失败: {str(e)}")
            return {
                "errors": state.get("errors", []) + [f"[{self.AGENT_NAME}]: {str(e)}"],
                "current_agent": self.AGENT_NAME,
                "execution_log": state.get("execution_log", []) + [{
                    "agent_name": self.AGENT_NAME,
                    "status": "error",
                    "error_message": str(e)
                }]
            }

    def _extract_input(self, state: AgentState) -> Dict[str, Any]:
        return {
            "topic": state.get("user_query", ""),
            "profile": state.get("student_profile"),
            "messages": state.get("messages", [])
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        profile = input_data["profile"] or {}

        prompt = f"""你是一位{profile.get('major', '计算机科学')}专业的资深教学专家。
为以下学生生成关于「{input_data['topic']}」的个性化讲解文档。

学生画像：
- 年级：{profile.get('grade_level', '未知')}
- 数学基础：{profile.get('math_foundation', 3)}/5 {'(较弱，需要更多基础解释)' if profile.get('math_foundation', 3) <= 2 else '(良好，可以深入)'}
- 编程经验：{profile.get('programming_exp', 3)}/5
- 学习风格：{profile.get('learning_style', '综合型')}
- 薄弱点：{', '.join(profile.get('weak_points', ['未知']))}
- 兴趣方向：{', '.join(profile.get('interests', []))}

要求（严格按Markdown格式）：
1. # 标题：知识点名称
2. ## 概念解释：用通俗易懂的语言解释（根据学生基础调整深度）
3. ## 数学原理：公式推导（基础差就简化，基础好则详细）
4. ## 代码示例：用{profile.get('preferred_language', 'Python')}编写完整可运行代码
5. ## 实际应用：结合{', '.join(profile.get('interests', ['通用场景']))}的应用案例
6. ## 常见误区：列出初学者容易犯的错误
7. ## 总结与思考题：2-3个引导性问题

字数要求：2000-3000字
语言风格：{'轻松活泼' if profile.get('grade_level') in ['大一', '大二'] else '严谨专业'}
"""

        result = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=f"你擅长将复杂概念简单化，特别擅长为{profile.get('grade_level', '')}学生定制教学内容。"
        )

        return {
            "content": result["content"],
            "title": input_data["topic"],
            "topic": input_data["topic"],
            "difficulty": self._assess_difficulty(profile),
            "estimated_time": len(result["content"]) // 15,
            "tags": [input_data["topic"], profile.get("major", "")]
        }

    def _assess_difficulty(self, profile):
        level = profile.get("ml_knowledge", 3) if profile else 3
        if level <= 2:
            return "beginner"
        elif level <= 4:
            return "intermediate"
        else:
            return "advanced"

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"document": output_data}
