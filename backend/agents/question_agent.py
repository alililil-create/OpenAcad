from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class QuestionAgent:
    """生成个性化练习题"""

    AGENT_NAME = "question_agent"

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
            "difficulty": self._get_difficulty_from_profile(state.get("student_profile"))
        }

    def _get_difficulty_from_profile(self, profile):
        if profile and "ml_knowledge" in profile:
            level = profile["ml_knowledge"]
            if level <= 2:
                return "基础"
            elif level <= 4:
                return "进阶"
            else:
                return "高级"
        return "中级"

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        profile = input_data["profile"] or {}

        prompt = f"""你是一个机器学习教学专家。为以下学生生成关于「{input_data['topic']}」的练习题。

学生水平：{input_data['difficulty']}
薄弱点：{', '.join(profile.get('weak_points', []))}
偏好编程语言：{profile.get('preferred_language', 'Python')}

请生成5道不同类型的题目（JSON格式）：
[
  {{
    "id": "q1",
    "type": "choice",
    "question": "单选题题目",
    "options": ["A选项", "B选项", "C选项", "D选项"],
    "answer": "B",
    "explanation": "详细解析",
    "difficulty": 2,
    "knowledge_point": "对应知识点",
    "hints": ["提示1", "提示2"]
  }},
  // ... 共5题，包含 choice/fill_blank/coding/case_study 类型
]

注意：
1. 题目难度要循序渐进
2. 要覆盖该知识点的核心概念
3. 解析要详细易懂
4. 编程题要有完整可运行代码
"""

        result = await llm.structured_output(
            messages=[{"role": "user", "content": prompt}],
            output_schema={
                "questions": [
                    {
                        "id": "", "type": "", "question": "",
                        "options": [], "answer": "",
                        "explanation": "", "difficulty": 3,
                        "knowledge_point": "", "hints": []
                    }
                ]
            },
            system_prompt="你擅长设计有针对性的练习题，能根据学生水平调整难度。"
        )

        return {"questions": result.get("questions", [])}

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"questions": output_data["questions"]}
