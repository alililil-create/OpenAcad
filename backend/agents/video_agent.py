from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
from config import settings
import time
import logging

logger = logging.getLogger(__name__)


class VideoAgent:
    AGENT_NAME = "generate_video"

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
            error_msg = str(e) or "未知错误"
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
        profile = state.get("student_profile") or {}
        return {
            "topic": state.get("user_query", ""),
            "profile": profile,
            "document": state.get("document"),
            "mindmap": state.get("mindmap"),
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not settings.OPENMAIC_ENABLED:
            logger.info(f"[{self.AGENT_NAME}] OpenMAIC 未启用，使用降级模式")
            return await self._process_fallback(input_data)

        profile = input_data["profile"]
        topic = input_data["topic"]

        llm = await get_llm_service()
        scene_prompt = await self._build_scene_prompt(llm, topic, profile)

        from services.video_service import generate_video

        user_id = profile.get("user_id", 0)

        logger.info(f"[{self.AGENT_NAME}] 调用 OpenMAIC 生成教学动画: "
                    f"topic={topic[:40]}, prompt={scene_prompt[:60]}...")

        video_data = await generate_video(
            prompt=scene_prompt,
            user_id=user_id,
            duration=5,
            ratio="16:9",
            resolution="720p",
        )

        return {
            "video_result": video_data,
            "skipped": False,
            "provider": "openmaic",
        }

    async def _process_fallback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data["topic"]
        profile = input_data["profile"]

        from services.video_service import generate_lecture_script
        script_data = await generate_lecture_script(topic, profile)

        return {
            "video_result": script_data,
            "skipped": False,
            "provider": "llm_fallback",
        }

    async def _build_scene_prompt(self, llm, topic: str, profile: dict) -> str:
        grade = profile.get("grade_level", "大学生")
        major = profile.get("major", "计算机")

        prompt = f"""为机器学习知识点「{topic}」生成一段详细的课堂教学描述，用于AI生成教学动画。

学生信息: {major}专业 {grade}

要求:
1. 描述这个知识点的核心概念和要点
2. 包含具体的数据、公式、或代码示例
3. 适合大学生的理解水平
4. 200-400字

直接输出教学内容，不要标记。"""

        result = await llm.chat([{"role": "user", "content": prompt}])
        scene_prompt = result.get("content", topic).strip()

        if len(scene_prompt) < 20:
            scene_prompt = f"详细讲解机器学习知识点「{topic}」，包括核心概念、数学原理、实际应用，面向{grade}{major}专业学生。"

        return scene_prompt

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        if output_data.get("skipped"):
            return {
                "video_result": None,
                "video_skipped": True,
            }

        video_data = output_data.get("video_result", {})
        return {
            "video_result": {
                "url": video_data.get("url", ""),
                "duration": video_data.get("duration", 0),
                "ratio": video_data.get("ratio", "16:9"),
                "resolution": video_data.get("resolution", "720p"),
                "object_name": video_data.get("object_name", ""),
                "stored_in_oss": video_data.get("stored_in_oss", False),
                "provider": output_data.get("provider", ""),
            },
            "video_skipped": False,
        }
