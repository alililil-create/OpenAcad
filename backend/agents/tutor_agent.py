from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class TutorAgent:
    """智能答疑辅导"""

    AGENT_NAME = "tutor_agent"

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
            "question": state.get("user_query", ""),
            "context": state.get("messages", []),
            "profile": state.get("student_profile"),
            "user_id": int(state.get("user_id") or 0),
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        profile = input_data["profile"] or {}

        prompt = f"""你是一个耐心的机器学习辅导老师。学生提出了以下问题：

问题：{input_data['question']}

对话上下文：
{input_data['context'][-5:] if input_data['context'] else '无'}

学生背景：
- 年级：{profile.get('grade_level', '未知')}
- 基础水平：数学{profile.get('math_foundation', 3)}/5，编程{profile.get('programming_exp', 3)}/5
- 薄弱点：{', '.join(profile.get('weak_points', []))}
- 学习风格：{profile.get('learning_style', '综合型')}

请给出详细的解答，包括：
1. **直接回答**：简洁明了的回答
2. **原理解释**：用通俗易懂的方式解释原理（根据学生水平调整深度）
3. **举例说明**：用具体例子帮助理解
4. **代码演示**（如适用）：提供{profile.get('preferred_language', 'Python')}代码示例
5. **常见误区**：指出初学者容易犯的错误
6. **延伸思考**：引导性的后续学习建议

回答要求：
- 语言亲切友好，像一对一辅导
- 循序渐进，不要一次性灌输太多
- 鼓励式教学，增强学生信心
- 字数500-800字
"""

        uid = int(input_data.get("user_id") or 0)
        result = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是一位经验丰富的机器学习导师，善于因材施教，能用最简单的语言解释复杂的概念。",
            cache_agent="tutor",
            cache_chapter="tutor",
            cache_stage="agent",
            cache_profile_hash=str(uid),
            cache_user_id=uid,
            use_cache=False,
            write_cache=False,
        )

        return {"response": result["content"]}

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"tutor_response": output_data["response"]}
