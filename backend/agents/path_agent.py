from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class PathAgent:
    """规划个性化学习路径"""

    AGENT_NAME = "path_agent"

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
            "goal": state.get("user_query", ""),
            "profile": state.get("student_profile"),
            "generated_resources": {
                "has_document": bool(state.get("document")),
                "has_questions": bool(state.get("questions")),
                "has_code": bool(state.get("code_examples")),
                "has_mindmap": bool(state.get("mindmap"))
            },
            "user_id": int(state.get("user_id") or 0),
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        profile = input_data["profile"] or {}

        prompt = f"""你是一个学习路径规划专家。根据学生的画像和学习目标，制定个性化的学习路径。

学习目标：{input_data['goal']}

学生画像：
- 专业：{profile.get('major', '未知')}
- 年级：{profile.get('grade_level', '未知')}
- 数学基础：{profile.get('math_foundation', 3)}/5
- 编程经验：{profile.get('programming_exp', 3)}/5
- ML知识：{profile.get('ml_knowledge', 2)}/5
- 每周可用时间：{profile.get('weekly_hours', 10)}小时
- 学习风格：{profile.get('learning_style', '综合型')}
- 薄弱点：{', '.join(profile.get('weak_points', []))}
- 兴趣方向：{', '.join(profile.get('interests', []))}

已生成的资源：
{input_data['generated_resources']}

请制定4-6个阶段的学习路径（JSON格式）：
[
  {{
    "step_number": 1,
    "topic": "阶段主题",
    "description": "详细描述",
    "resources": [{{"type": "文档/视频/代码/练习", "title": "资源名称"}}],
    "estimated_hours": 10,
    "prerequisites": ["前置知识"],
    "status": "not_started"
  }}
]

要求：
1. 路径要符合认知规律，由浅入深
2. 每个阶段有明确的学习目标和产出
3. 考虑学生的时间安排（每周{profile.get('weekly_hours', 10)}小时）
4. 针对薄弱环节加强训练
5. 结合学生的兴趣方向
6. 总时长控制在8-12周
"""

        uid = int(input_data.get("user_id") or 0)
        result = await llm.structured_output(
            messages=[{"role": "user", "content": prompt}],
            output_schema={
                "learning_path": [
                    {
                        "step_number": 1, "topic": "", "description": "",
                        "resources": [], "estimated_hours": 10,
                        "prerequisites": [], "status": "not_started"
                    }
                ]
            },
            system_prompt="你是教育规划专家，擅长根据学生特点制定科学的学习路径。",
            cache_user_id=uid,
        )

        return {"path": result.get("learning_path", [])}

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"learning_path": output_data["path"]}
