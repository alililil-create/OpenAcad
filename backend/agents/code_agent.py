from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class CodeAgent:
    """生成代码实操案例"""

    AGENT_NAME = "code_agent"

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
            error_msg = str(e) or "未知错误（可能是API响应为空或JSON解析失败）"
            logger.error(f"[{self.AGENT_NAME}] 处理失败: {error_msg}")
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
            "language": (state.get("student_profile") or {}).get("preferred_language", "Python")
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        profile = input_data["profile"] or {}
        language = input_data["language"]

        prompt = f"""你是一个{language}编程教育专家。为「{input_data['topic']}」生成实用的代码实操案例。

学生编程经验：{profile.get('programming_exp', 3)}/5
学习目标：{profile.get('learning_goal', '掌握基础知识')}

请生成2-3个代码示例（JSON格式）：
[
  {{
    "title": "示例标题",
    "language": "{language}",
    "code": "完整的可运行代码（带注释）",
    "explanation": "代码功能说明",
    "comments": ["逐行注释1", "逐行注释2"],
    "expected_output": "运行结果示例",
    "prerequisites": ["前置知识1"],
    "complexity": "初级/中级/高级"
  }}
]

要求：
1. 代码必须完整可运行
2. 注释详尽，适合{profile.get('grade_level', '')}学生理解
3. 从简单到复杂递进
4. 包含实际应用场景
5. 使用真实的库和API
"""

        result = await llm.structured_output(
            messages=[{"role": "user", "content": prompt}],
            output_schema={
                "code_examples": [
                    {
                        "title": "", "language": language,
                        "code": "", "explanation": "",
                        "comments": [], "expected_output": "",
                        "prerequisites": [], "complexity": "中级"
                    }
                ]
            },
            system_prompt=f"你擅长编写教学用的{language}代码，注重代码质量和可读性。"
        )

        return {"code_examples": result.get("code_examples", [])}

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"code_examples": output_data["code_examples"]}
