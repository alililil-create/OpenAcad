from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class MindmapAgent:
    """生成思维导图(Markdown格式)"""

    AGENT_NAME = "mindmap_agent"

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
            "document_content": state.get("document", {}).get("content", "") if state.get("document") else "",
            "user_id": int(state.get("user_id") or 0),
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        profile = input_data["profile"] or {}

        prompt = f"""你是一个知识结构化专家。为「{input_data['topic']}」这个知识点生成思维导图内容。

学生年级：{profile.get('grade_level', '未知')}
已有文档内容摘要：{input_data['document_content'][:500] if input_data['document_content'] else '无'}
[uid={input_data.get('user_id', 0)}]

请以Markdown格式生成思维导图（使用缩进表示层级关系）：

# {input_data['topic']}

## 核心概念
### 定义
### 特点
### 应用场景

## 关键公式/定理
### 公式1
### 公式2

## 算法流程
### 步骤1
### 步骤2

## 相关概念
### 概念A
### 概念B

## 常见问题
### 问题1
### 问题2

要求：
1. 层级清晰，一般3-4层
2. 覆盖该知识点的完整体系
3. 重点突出核心概念
4. 适合用Markmap等工具渲染
"""

        uid = int(input_data.get("user_id") or 0)
        result = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你擅长将复杂知识体系整理成清晰的思维导图结构。",
            cache_user_id=uid,
            use_cache=False,
            write_cache=False,
        )

        return {"mindmap_content": result["content"]}

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"mindmap": output_data["mindmap_content"]}
