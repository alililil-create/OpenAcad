"""
画像 Agent — 通过自然语言对话自动构建 6 大类 25+ 维度机器学习学生画像

核心设计：
1. 无需表单，纯对话提取特征
2. 首次对话 → 构建完整画像
3. 后续对话 → 增量优化（基于对话中暴露的新信息调整对应维度）
4. 所有 7 个 Agent 共享画像 → 统一个性化
"""

from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import json
import logging

logger = logging.getLogger(__name__)

# 默认技能矩阵模板
DEFAULT_SKILL_MATRIX = {
    "math": {"linear_algebra": 1, "probability": 1, "calculus": 1, "statistics": 1, "optimization": 1},
    "programming": {"python": 1, "numpy": 1, "pandas": 1, "data_structure": 1, "algorithm": 1, "sql": 1},
    "machine_learning": {
        "supervised": 1, "unsupervised": 1, "neural_networks": 1, "deep_learning": 1,
        "nlp": 1, "cv": 1, "reinforcement": 1, "feature_engineering": 1,
        "model_evaluation": 1, "mlops": 1, "ensemble_methods": 1
    },
    "tools": {"sklearn": 1, "pytorch": 1, "tensorflow": 1, "jupyter": 1, "git": 1, "docker": 1, "matplotlib": 1, "mlflow": 1}
}


def _deep_merge(base: dict, update: dict) -> dict:
    """深度合并两个 dict，update 中的空值不覆盖 base"""
    result = dict(base)
    for key, val in update.items():
        if key not in result:
            result[key] = val
        elif isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        elif val is not None and val != "" and val != [] and val != {}:
            result[key] = val
    return result


class ProfileAgent:
    """通过对话抽取学生特征，构建 ≥ 25 维度的 ML 专属动态画像"""

    AGENT_NAME = "profile_agent"

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        start_time = time.time()

        try:
            logger.info(f"[{self.AGENT_NAME}] 开始画像分析...")

            input_data = self._extract_input(state)
            output_data = await self._process(input_data)
            result = self._build_result(output_data)

            execution_time = time.time() - start_time
            log_entry = {
                "agent_name": self.AGENT_NAME,
                "start_time": start_time,
                "end_time": time.time(),
                "status": "success",
                "processing_time": execution_time
            }

            logger.info(f"[{self.AGENT_NAME}] 完成，耗时 {execution_time:.2f}s")

            return {
                **result,
                "current_agent": self.AGENT_NAME,
                "execution_log": state.get("execution_log", []) + [log_entry],
                "processing_time": {**(state.get("processing_time", {})), self.AGENT_NAME: execution_time}
            }

        except Exception as e:
            logger.error(f"[{self.AGENT_NAME}] 失败: {str(e)}")
            return {
                "errors": state.get("errors", []) + [f"[{self.AGENT_NAME}]: {str(e)}"],
                "current_agent": self.AGENT_NAME,
                "execution_log": state.get("execution_log", []) + [{"agent_name": self.AGENT_NAME, "status": "error", "error_message": str(e)}]
            }

    def _extract_input(self, state: AgentState) -> Dict[str, Any]:
        return {
            "messages": state.get("messages", []),
            "user_query": state.get("user_query", ""),
            "existing_profile": state.get("student_profile"),
            "user_id": int(state.get("user_id") or 0),
        }

    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = await get_llm_service()
        existing = input_data.get('existing_profile')
        has_profile = existing and isinstance(existing, dict) and existing.get("major")

        # 准备对话历史
        messages = input_data.get("messages", [])
        history_text = ""
        for m in messages[-15:]:  # 最近15条
            role = "学生" if m.get("role") == "user" else "助手"
            content = str(m.get("content", ""))[:300]
            history_text += f"{role}: {content}\n"
        if not history_text:
            history_text = "（首次对话，无历史）"

        user_query = input_data.get("user_query", "")

        # ===== 构建 Prompt =====
        if has_profile:
            prompt = f"""你是机器学习教育画像分析专家。学生已有画像，请基于最新对话进行**增量优化**。

【已有完整画像（优先保留）】：
{json.dumps(existing, ensure_ascii=False, indent=2)}

【最近对话历史】：
{history_text}

【学生最新发言】：{user_query}

请分析最新对话中有哪些**新的信息**，对画像进行小幅调整。未涉及的维度保持原值不变。
如果新对话确认了原有判断，将 confidence_score 提高 0.05-0.1。
如果新对话暴露了错误理解或知识盲点，追加到 misconception_archive。
如果新对话展现了学习状态（坚持度、求助频率等），更新 behavior_pattern。

返回完整的 JSON 画像："""
        else:
            prompt = f"""你是机器学习教育画像分析专家。这是**首次对话**，请从对话中尽可能多地提取学生特征。

【对话内容】：
{history_text}

【学生最新发言】：{user_query}

请从对话中提取以下 6 大类信息，构建完整的机器学习学生画像。
**重要：你是从对话中提取，不要编造！不确定的维度留空或给保守值。**

返回完整的 JSON 画像："""

        # 通用输出格式（首次和增量共用）
        prompt += r"""
{
  // ========== 一、基础档案 ==========
  "major": "专业（如计算机科学/数学/电子信息/其他）",
  "grade_level": "大一/大二/大三/大四/研一/研二/研三/已工作",
  "target_role": "目标职业（算法工程师/数据科学家/机器学习研究员/转行求职者/学术研究）",
  "prior_courses": ["已修课程1", "已修课程2"],
  "preferred_language": "Python/R/Julia",

  // ========== 二、技能热力图（1-5，1=完全不会，5=精通）==========
  "skill_matrix": {
    "math": {
      "linear_algebra": 1-5,  "probability": 1-5,  "calculus": 1-5,
      "statistics": 1-5,       "optimization": 1-5
    },
    "programming": {
      "python": 1-5,  "numpy": 1-5,  "pandas": 1-5,
      "data_structure": 1-5, "algorithm": 1-5, "sql": 1-5
    },
    "machine_learning": {
      "supervised": 1-5,     "unsupervised": 1-5,    "neural_networks": 1-5,
      "deep_learning": 1-5,  "nlp": 1-5,             "cv": 1-5,
      "reinforcement": 1-5,  "feature_engineering": 1-5,
      "model_evaluation": 1-5, "mlops": 1-5,         "ensemble_methods": 1-5
    },
    "tools": {
      "sklearn": 1-5,  "pytorch": 1-5,  "tensorflow": 1-5,
      "jupyter": 1-5,  "git": 1-5,      "docker": 1-5,
      "matplotlib": 1-5, "mlflow": 1-5
    }
  },

  // ========== 三、认知画像 ==========
  "cognitive_profile": {
    "bloom_level": "remember/understand/apply/analyze/evaluate/create",
    "learning_style": "visual/auditory/reading/kinesthetic",
    "abstraction_ability": 1-5,
    "mathematical_maturity": 1-5,
    "question_depth": "surface/medium/deep",
    "learning_pace": "slow/medium/fast",
    "prefers_theory_first": true/false,
    "needs_concrete_examples": true/false,
    "attention_to_detail": 1-5
  },

  // ========== 四、易错档案 ==========
  "misconception_archive": {
    "concept_misunderstandings": [
      {"concept": "概念名", "error": "错误理解", "frequency": 出现次数}
    ],
    "math_blind_spots": ["薄弱数学点1"],
    "coding_bad_habits": ["代码坏习惯1"],
    "high_error_topics": ["常错主题1"],
    "exam_mistake_types": [
      {"type": "推导/代码/概念/调参", "error_rate": 0.0-1.0}
    ]
  },

  // ========== 五、学习行为 ==========
  "behavior_pattern": {
    "completion_rate": 0.0-1.0,
    "avg_session_minutes": 预计每次学习分钟数,
    "active_time_of_day": "morning/afternoon/evening/night",
    "content_format_preference": ["document","video","code","interactive"],
    "exercise_type_preference": "multiple_choice/coding/project/open_ended",
    "hint_usage_rate": 0.0-1.0,
    "review_frequency": 0.0-1.0,
    "drop_off_topics": ["可能放弃的主题"],
    "persistence_score": 1-5
  },

  // ========== 六、动机画像 ==========
  "motivation_profile": {
    "primary_motivation": "job_hunting/research/career_change/curiosity/exam",
    "urgency_level": 1-5,
    "self_efficacy": 1-5,
    "topic_passion": [
      {"topic": "感兴趣的话题", "interest": 0.0-1.0}
    ],
    "career_target": "目标岗位/方向",
    "burnout_risk": "low/medium/high",
    "preferred_reward": "achievement/progress/social"
  },

  "confidence_score": 0.0-1.0,
  "profile_version": 数字
}

要求：
1. skill_matrix 中用 3 分代表"可能了解"，不要全部给 1 或全部给 4-5
2. cognitive_profile 基于提问方式推断（问 why 是 deep，问 how 是 surface）
3. misconception_archive 从"我老是搞混""这个不太理解"等表述中提取
4. motivation_profile 从"想找工作""对XX感兴趣""下周面试"中推断
5. behavior_pattern 首次对话可给默认值，后续更新
6. 不确定的字段用 null 或保持原值，不要编造
"""

        # 调用 LLM 生成结构化画像
        output_schema = {
            "major": "", "grade_level": "", "target_role": "",
            "prior_courses": [], "preferred_language": "",
            "skill_matrix": DEFAULT_SKILL_MATRIX,
            "cognitive_profile": {
                "bloom_level": "understand", "learning_style": "reading",
                "abstraction_ability": 3, "mathematical_maturity": 3,
                "question_depth": "medium", "learning_pace": "medium",
                "prefers_theory_first": False, "needs_concrete_examples": True,
                "attention_to_detail": 3
            },
            "misconception_archive": {
                "concept_misunderstandings": [],
                "math_blind_spots": [],
                "coding_bad_habits": [],
                "high_error_topics": [],
                "exam_mistake_types": []
            },
            "behavior_pattern": {
                "completion_rate": 0.7, "avg_session_minutes": 45,
                "active_time_of_day": "evening",
                "content_format_preference": ["document", "code"],
                "exercise_type_preference": "coding",
                "hint_usage_rate": 0.3, "review_frequency": 0.5,
                "drop_off_topics": [], "persistence_score": 3
            },
            "motivation_profile": {
                "primary_motivation": "curiosity", "urgency_level": 3,
                "self_efficacy": 3, "topic_passion": [],
                "career_target": "", "burnout_risk": "medium",
                "preferred_reward": "progress"
            },
            "confidence_score": 0.5, "profile_version": 1
        }

        uid = int(input_data.get("user_id") or 0)
        result = await llm.structured_output(
            messages=[{"role": "user", "content": prompt}],
            output_schema=output_schema,
            system_prompt="你是机器学习教育画像分析专家。从对话中精确提取学生特征，不编造不确定的信息。skill_matrix 评分需要分布在 1-5 范围内，不要全部给中间值。",
            cache_user_id=uid,
        )

        # 深度合并已有画像
        if has_profile:
            merged = _deep_merge(existing, result)
            merged["confidence_score"] = min(1.0, merged.get("confidence_score", 0.5) + 0.03)
            merged["profile_version"] = existing.get("profile_version", 0) + 1
            return {"profile": merged}

        result["profile_version"] = 1
        if result.get("confidence_score", 0.5) < 0.4:
            result["confidence_score"] = 0.4  # 首次画像最少 0.4
        return {"profile": result}

    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        profile = output_data.get("profile", {})
        return {
            "student_profile": profile,
            "profile_confidence": profile.get("confidence_score", 0.5)
        }