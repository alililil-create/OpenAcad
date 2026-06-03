"""
画像构建向导 API — 6 阶段流程

阶段 0: 注册后自动进入
阶段 1: 上传学习背景文档 (PDF/DOCX/TXT/MD)
阶段 2: 选择学科 (机器学习)
阶段 3: 知识问答 (15题自适应)
阶段 4: 画像生成 (文档+问答 → capability_matrix)
阶段 5: 画像展示与确认 (手动微调)
阶段 6: 学习资料生成 (基于低分知识点)
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
import json

import database.connection as db_conn
from database.models import User, StudentProfile
from services.document_parser import document_parser
from services.question_bank import (
    get_question, get_questions_by_chapter, get_all_chapters,
    CHAPTER_ALLOCATION, get_chapter_names, QUESTIONS
)
from services.profile_engine import profile_engine
from services.cache_service import CacheService
from services.knowledge_graph import get_knowledge_graph, get_recommended_path, trace_root_cause, build_reverse_dependencies, CHAPTER_ORDER

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wizard", tags=["wizard"])

# 存储答题进度的简单缓存（生产环境应该放 Redis）
quiz_progress_store: Dict[int, Dict[str, Any]] = {}


# ===== Pydantic 模型 =====

class QuizAnswer(BaseModel):
    question_id: str
    selected_option: int  # -1 表示"不知道"


class SubmitQuizRequest(BaseModel):
    answers: List[QuizAnswer]


class BasicInfoRequest(BaseModel):
    major: Optional[str] = None
    degree: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    preferred_language: Optional[str] = None


class LearningGoalsRequest(BaseModel):
    target_role: Optional[str] = None
    deadline: Optional[str] = None
    motivation: Optional[str] = None
    weekly_hours: Optional[int] = None


class PriorExperienceRequest(BaseModel):
    courses_taken: Optional[List[str]] = None
    projects: Optional[List[str]] = None
    self_assessment: Optional[str] = None


class ProfileConfirmRequest(BaseModel):
    adjustments: Optional[Dict[str, Any]] = None  # {chapter: {kp: score_adjustment}}
    notes: Optional[str] = None


class ChapterQuestion(BaseModel):
    question_id: str
    chapter: str
    question: str
    options: List[str]
    difficulty: int


# ===== 阶段 0: 检查画像状态 =====

@router.get("/status/{user_id}")
async def check_wizard_status(user_id: int):
    """检查用户是否需要走画像构建向导"""
    async with db_conn._async_session_factory() as db:
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        has_profile = profile is not None
        has_capability = has_profile and profile.capability_matrix is not None
        has_document = has_profile and profile.profile_detail is not None and \
            profile.profile_detail.get("uploaded_document") is not None

        return {
            "success": True,
            "needs_wizard": not has_capability,
            "stages_completed": {
                "stage_0_registered": True,
                "stage_1_document": has_document,
                "stage_2_subject": has_profile,
                "stage_3_quiz": has_capability,
                "stage_4_profile_generated": has_capability,
                "stage_5_confirmed": has_profile and profile.profile_version > 1
            }
        }


# ===== 阶段 1: 文档上传（增强版 — 上传后自动调用画像构建Agent）=====

@router.post("/upload-document/{user_id}")
async def upload_document(user_id: int, file: UploadFile = File(...)):
    """上传学习背景文档并解析 + 自动调用画像构建Agent提取结构化画像数据"""
    # 检查格式
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in document_parser.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400, f"不支持的格式: {ext}，支持: {document_parser.SUPPORTED_EXTENSIONS}"
        )

    # 保存到临时目录
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{user_id}_{file.filename}")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 解析文档
    try:
        result = await document_parser.parse(file_path)
    except Exception as e:
        logger.error(f"文档解析失败: {e}")
        raise HTTPException(500, f"文档解析失败: {str(e)}")

    # 清理临时文件
    try:
        os.remove(file_path)
    except:
        pass

    # 存储解析结果到画像表
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        if not profile:
            profile = StudentProfile(user_id=user_id, profile_version=0)
            db.add(profile)

        # 更新 profile_detail
        existing_detail = profile.profile_detail or {}
        existing_detail["uploaded_document"] = {
            "format": result["format"],
            "char_count": result["char_count"],
            "extracted_info": result["extracted_info"]
        }
        profile.profile_detail = existing_detail
        await db.commit()

    # 调用画像构建Agent从文档中提取结构化画像数据
    profile_extracted = None
    raw_text = result.get("raw_text", "")
    extracted_info = result.get("extracted_info", {})
    doc_text_for_llm = raw_text[:8000] if raw_text else ""

    if doc_text_for_llm and len(doc_text_for_llm) > 50:
        try:
            profile_extracted = await _extract_profile_from_document(doc_text_for_llm, extracted_info)
            if profile_extracted:
                async with db_conn._async_session_factory() as db:
                    result_obj = await db.execute(
                        select(StudentProfile).where(StudentProfile.user_id == user_id)
                    )
                    profile = result_obj.scalar_one_or_none()
                    if profile:
                        existing_detail = dict(profile.profile_detail or {})
                        existing_detail["pending_profile_data"] = profile_extracted
                        existing_detail["pending_profile_source"] = "document"
                        existing_detail["pending_profile_at"] = datetime.now().isoformat()

                        existing_detail["basic_info"] = {
                            "major": profile_extracted.get("major") or "",
                            "grade": profile_extracted.get("grade_level") or "",
                            "preferred_language": profile_extracted.get("preferred_language") or ""
                        }
                        existing_detail["learning_goals"] = {
                            "target_role": profile_extracted.get("target_role") or "",
                            "motivation": (profile_extracted.get("motivation_profile") or {}).get("primary_motivation") or ""
                        }

                        if profile_extracted.get("major"):
                            profile.major = profile_extracted["major"]
                        if profile_extracted.get("grade_level"):
                            profile.grade_level = profile_extracted["grade_level"]
                        if profile_extracted.get("target_role"):
                            profile.target_role = profile_extracted["target_role"]
                        if profile_extracted.get("preferred_language"):
                            profile.preferred_language = profile_extracted["preferred_language"]
                        if profile_extracted.get("prior_courses"):
                            profile.prior_courses = profile_extracted["prior_courses"]

                        profile.profile_detail = existing_detail
                        await db.commit()
                        logger.info(f"[Wizard] 画像构建Agent提取的数据已暂存: user_id={user_id}")
        except Exception as e:
            logger.warning(f"[Wizard] 画像构建Agent提取失败（不影响上传）: {e}")

    return {
        "success": True,
        "data": {
            "format": result["format"],
            "char_count": result["char_count"],
            "extracted_info": result["extracted_info"],
            "profile_extracted": profile_extracted,
            "has_profile_data": profile_extracted is not None and len(profile_extracted) > 0
        }
    }


async def _extract_profile_from_document(doc_text: str, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """调用LLM从文档中提取结构化画像数据"""
    from services.llm_service import get_llm_service

    llm = await get_llm_service()

    education_text = json.dumps(extracted_info.get("education", {}), ensure_ascii=False)
    courses_text = json.dumps(extracted_info.get("courses_taken", []), ensure_ascii=False)
    projects_text = json.dumps(extracted_info.get("projects", []), ensure_ascii=False)
    skills_text = json.dumps(extracted_info.get("self_assessment", []), ensure_ascii=False)

    prompt = f"""你是机器学习教育画像分析专家。请从以下学生提交的文档中提取结构化画像数据。

【文档内容】：
{doc_text}

【已提取的结构化线索】：
教育背景：{education_text}
已修课程：{courses_text}
项目经历：{projects_text}
技能自述：{skills_text}

请从以上信息中提取以下 6 大类画像数据。不确定的字段用 null，不要编造。

返回纯 JSON（不要用 markdown 代码块包裹）："""

    prompt += r"""
{
  "major": "专业名称或null",
  "grade_level": "大一/大二/大三/大四/研一/研二/研三/已工作 或 null",
  "target_role": "目标职业或null",
  "prior_courses": ["课程1", "课程2"] 或 [],
  "preferred_language": "Python/R/Julia 或 null",

  "skill_matrix": {
    "math": {"linear_algebra": 1-5或null, "probability": 1-5或null, "calculus": 1-5或null, "statistics": 1-5或null, "optimization": 1-5或null},
    "programming": {"python": 1-5或null, "numpy": 1-5或null, "pandas": 1-5或null, "data_structure": 1-5或null, "algorithm": 1-5或null, "sql": 1-5或null},
    "machine_learning": {"supervised": 1-5或null, "unsupervised": 1-5或null, "neural_networks": 1-5或null, "deep_learning": 1-5或null, "nlp": 1-5或null, "cv": 1-5或null, "reinforcement": 1-5或null, "feature_engineering": 1-5或null, "model_evaluation": 1-5或null, "mlops": 1-5或null, "ensemble_methods": 1-5或null},
    "tools": {"sklearn": 1-5或null, "pytorch": 1-5或null, "tensorflow": 1-5或null, "jupyter": 1-5或null, "git": 1-5或null, "docker": 1-5或null, "matplotlib": 1-5或null, "mlflow": 1-5或null}
  },

  "cognitive_profile": {
    "bloom_level": "remember/understand/apply/analyze/evaluate/create 或 null",
    "learning_style": "visual/auditory/reading/kinesthetic 或 null",
    "abstraction_ability": 1-5或null,
    "mathematical_maturity": 1-5或null,
    "learning_pace": "slow/medium/fast 或 null",
    "prefers_theory_first": true/false/null,
    "needs_concrete_examples": true/false/null
  },

  "motivation_profile": {
    "primary_motivation": "job_hunting/research/career_change/curiosity/exam 或 null",
    "urgency_level": 1-5或null,
    "self_efficacy": 1-5或null,
    "topic_passion": [{"topic": "主题", "interest": 0.0-1.0}],
    "career_target": "目标岗位或null"
  },

  "confidence_score": 0.0-1.0
}

要求：
1. 从文档中尽可能多地提取信息，不确定的字段给 null
2. skill_matrix 中，如果文档提到"学过/掌握/熟悉"某技能给 3-4 分，"了解"给 2 分，"精通"给 5 分
3. prior_courses 从课程列表和技能描述中提取
4. motivation_profile 从项目经历和目标描述中推断
5. confidence_score 表示你对提取结果的信心（0-1），信息越多分数越高
"""

    try:
        result = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是机器学习教育画像分析专家。从文档中精确提取学生特征，不编造不确定的信息。返回纯JSON。",
            temperature=0.2
        )
        content = result.get("content", "")
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
    except Exception as e:
        logger.error(f"[Wizard] LLM画像提取失败: {e}")
        return {}


def _apply_profile_extraction(profile: StudentProfile, data: Dict[str, Any]):
    """将LLM提取的画像数据应用到数据库模型"""
    if not data:
        return

    if data.get("major"):
        profile.major = data["major"]
    if data.get("grade_level"):
        profile.grade_level = data["grade_level"]
    if data.get("target_role"):
        profile.target_role = data["target_role"]
    if data.get("prior_courses"):
        profile.prior_courses = data["prior_courses"]
    if data.get("preferred_language"):
        profile.preferred_language = data["preferred_language"]
    if data.get("skill_matrix"):
        existing = profile.skill_matrix or {}
        for category, skills in data["skill_matrix"].items():
            if isinstance(skills, dict):
                if category not in existing:
                    existing[category] = {}
                for sk, sv in skills.items():
                    if sv is not None:
                        existing[category][sk] = sv
        profile.skill_matrix = existing
    if data.get("cognitive_profile"):
        existing_cog = profile.cognitive_profile or {}
        cog = data["cognitive_profile"]
        for k, v in cog.items():
            if v is not None:
                existing_cog[k] = v
        profile.cognitive_profile = existing_cog
    if data.get("motivation_profile"):
        profile.motivation_profile = data["motivation_profile"]

    existing_detail = profile.profile_detail or {}
    existing_detail["llm_extracted"] = data
    existing_detail["llm_extracted_at"] = datetime.now().isoformat()
    profile.profile_detail = existing_detail
    profile.profile_version = (profile.profile_version or 0) + 1


# ===== 阶段 2: 获取学科列表 + 章节信息 =====

@router.get("/subjects")
async def get_subjects():
    """获取可选学科列表"""
    return {
        "success": True,
        "data": {
            "subjects": [
                {"id": "machine_learning", "name": "机器学习", "chapters": 9, "knowledge_points": 45}
            ]
        }
    }


@router.get("/chapters")
async def get_chapters():
    """获取所有章节信息和题数分配"""
    chapters = []
    chapter_names = get_chapter_names()
    for ch_id, alloc in CHAPTER_ALLOCATION.items():
        chapters.append({
            "id": ch_id,
            "name": chapter_names.get(ch_id, ch_id),
            "total_questions": alloc["total"],
            "required_correct": alloc["required"]
        })
    return {"success": True, "data": {"chapters": chapters, "total": 15}}


# ===== 知识图谱 API =====

@router.get("/knowledge-graph")
async def get_knowledge_graph_endpoint():
    """获取完整知识图谱（7章 + 依赖关系）"""
    graph = get_knowledge_graph()
    reverse_deps = build_reverse_dependencies()
    return {
        "success": True,
        "data": {
            "graph": graph,
            "reverse_dependencies": reverse_deps,
            "chapter_order": list(graph.keys())
        }
    }


@router.get("/knowledge-graph/recommended-path/{user_id}")
async def get_recommended_path_endpoint(user_id: int):
    """根据用户画像生成推荐学习路径（严格按 user_id 隔离）"""
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id 无效")
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        chapter_scores = {}
        if profile and profile.capability_matrix:
            for ch_id, ch_data in profile.capability_matrix.items():
                if isinstance(ch_data, dict):
                    score = ch_data.get("章节掌握度", {}).get("score", 0)
                    chapter_scores[ch_id] = round(score * 20)
                else:
                    chapter_scores[ch_id] = ch_data

        path = get_recommended_path(chapter_scores)
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "path": path,
                "chapter_scores": chapter_scores,
                "has_profile": profile is not None,
            }
        }


@router.get("/knowledge-graph/personalized-graph/{user_id}")
async def get_personalized_graph(user_id: int):
    """获取个性化神经网络结构图数据（按用户画像定制节点大小、推荐路径、重点标记）"""
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id 无效")

    graph = get_knowledge_graph()

    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        chapter_scores = {}
        if profile and profile.capability_matrix:
            for ch_id, ch_data in profile.capability_matrix.items():
                if isinstance(ch_data, dict):
                    score = ch_data.get("章节掌握度", {}).get("score", 0)
                    chapter_scores[ch_id] = round(score * 20)
                else:
                    chapter_scores[ch_id] = ch_data

    # 计算节点个性化数据
    node_personalization = {}
    for ch_id in CHAPTER_ORDER:
        ch = graph.get(ch_id, {})
        score = chapter_scores.get(ch_id, 0)
        mastery = score / 100 * 5

        # 确定节点状态
        locked = False
        for dep in ch.get("depends_on", []):
            if chapter_scores.get(dep, 0) / 100 * 5 < 1.0:
                locked = True
                break

        if locked:
            state = "locked"
        elif mastery >= 4.0:
            state = "active"
        elif mastery >= 2.5:
            state = "partial"
        elif mastery > 0:
            state = "weak"
        else:
            state = "inactive"

        # 节点大小：薄弱 → 大（需要关注），已掌握 → 小
        if state == "locked":
            node_size = 0.8
            emphasis = 0
        elif state == "active":
            node_size = 0.75
            emphasis = 0
        elif state == "weak":
            node_size = 1.25
            emphasis = 2
        elif state == "partial":
            node_size = 1.0
            emphasis = 1
        else:
            node_size = 1.1
            emphasis = 1

        # 确定推荐优先级
        if locked:
            priority = 4
        elif state == "weak":
            priority = 0
        elif state == "partial":
            priority = 1
        elif state == "inactive":
            priority = 2
        else:
            priority = 3

        node_personalization[ch_id] = {
            "score": score,
            "mastery": round(mastery, 1),
            "state": state,
            "node_size": node_size,
            "emphasis": emphasis,
            "priority": priority,
            "is_locked": locked,
            "locked_by": [d for d in ch.get("depends_on", []) if chapter_scores.get(d, 0) / 100 * 5 < 1.0]
        }

    # 计算推荐学习路径上的连接
    recommended_connections = []
    sorted_chapters = sorted(
        [(cid, node_personalization[cid]["priority"], node_personalization[cid]["mastery"])
         for cid in CHAPTER_ORDER],
        key=lambda x: (x[1], x[2])
    )

    next_focus = None
    for cid, pri, _ in sorted_chapters:
        if pri <= 2 and not node_personalization[cid]["is_locked"]:
            next_focus = cid
            break

    # 标记推荐路径上的连接
    if next_focus:
        visited = set()

        def mark_upstream_path(ch_id):
            if ch_id in visited:
                return
            visited.add(ch_id)
            ch = graph.get(ch_id, {})
            for dep in ch.get("depends_on", []):
                conn_key = f"{dep}->{ch_id}"
                if conn_key not in recommended_connections:
                    recommended_connections.append(conn_key)
                mark_upstream_path(dep)

        def mark_downstream_path(ch_id):
            if ch_id in visited:
                return
            visited.add(ch_id)
            rev_deps = build_reverse_dependencies()
            for downstream in rev_deps.get(ch_id, []):
                conn_key = f"{ch_id}->{downstream}"
                if conn_key not in recommended_connections:
                    recommended_connections.append(conn_key)
                mark_downstream_path(downstream)

        mark_upstream_path(next_focus)
        visited = set()
        mark_downstream_path(next_focus)

    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "has_profile": profile is not None,
            "chapter_scores": chapter_scores,
            "node_personalization": node_personalization,
            "next_focus": next_focus,
            "recommended_connections": recommended_connections,
            "graph": graph,
            "chapter_order": CHAPTER_ORDER
        }
    }


@router.get("/knowledge-graph/root-cause/{user_id}/{chapter_id}")
async def get_root_cause_endpoint(user_id: int, chapter_id: str):
    """病根溯源：分析某章节薄弱的前置依赖原因（严格按 user_id 隔离）"""
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id 无效")
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        chapter_scores = {}
        if profile and profile.capability_matrix:
            for ch_id, ch_data in profile.capability_matrix.items():
                if isinstance(ch_data, dict):
                    score = ch_data.get("章节掌握度", {}).get("score", 0)
                    chapter_scores[ch_id] = round(score * 20)
                else:
                    chapter_scores[ch_id] = ch_data

        result = trace_root_cause(chapter_id, chapter_scores)
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "chapter_id": chapter_id,
                **result,
            }
        }


# ===== 阶段 3: 自适应答题 =====

@router.get("/question/{chapter}/{index}")
async def get_next_question(
    chapter: str,
    index: int,
    user_id: int,
    previous_correct: Optional[bool] = None
):
    """
    获取下一道题 — 支持自适应跳题逻辑

    规则:
    - 用户答对某章节 required 数量后，跳过后续题
    - 答错则追加同章节下一道（不超过 total）
    """
    questions = get_questions_by_chapter(chapter)
    if not questions:
        raise HTTPException(404, f"未知章节: {chapter}")

    alloc = CHAPTER_ALLOCATION.get(chapter, {})
    required = alloc.get("required", 1)
    total = alloc.get("total", len(questions))

    # 追踪该章节的答题状态
    key = f"{user_id}_{chapter}"
    if key not in quiz_progress_store:
        quiz_progress_store[key] = {"correct": 0, "asked": 0, "last_correct": None}

    progress = quiz_progress_store[key]

    if previous_correct is not None:
        progress["asked"] += 1
        progress["last_correct"] = previous_correct
        if previous_correct:
            progress["correct"] += 1

    # 自适应跳题: 如果已答对 required 道 → 跳过本章剩余
    if progress["correct"] >= required:
        return {
            "success": True,
            "data": {
                "skip_chapter": True,
                "message": f"本章已达标（{progress['correct']}/{required}），跳过剩余题目",
                "chapter": chapter,
                "progress": {"correct": progress["correct"], "required": required}
            }
        }

    # 如果已答完所有题
    if progress["asked"] >= total:
        return {
            "success": True,
            "data": {
                "chapter_complete": True,
                "message": "本章所有题目已答完",
                "chapter": chapter,
                "progress": {"correct": progress["correct"], "total": total}
            }
        }

    # 获取当前题目
    q_idx = min(index, len(questions) - 1)
    q = questions[q_idx]

    return {
        "success": True,
        "data": {
            "skip_chapter": False,
            "question": {
                "id": q["id"],
                "chapter": q["chapter"],
                "question": q["question"],
                "options": q["options"]
            },
            "progress": {
                "correct": progress["correct"],
                "required": required,
                "total": total,
                "asked": progress["asked"]
            },
            "chapter_index": list(CHAPTER_ALLOCATION.keys()).index(chapter),
            "total_chapters": len(CHAPTER_ALLOCATION)
        }
    }


@router.post("/submit-answer/{user_id}")
async def submit_answer(user_id: int, answer: QuizAnswer):
    """提交单题答案，返回正确/错误 + 解析"""
    q = get_question(answer.question_id)
    if not q:
        raise HTTPException(404, f"题目不存在: {answer.question_id}")

    is_interest = q["answer"] == -1  # 兴趣探测题
    is_correct = answer.selected_option == q["answer"] if not is_interest else True

    # 记录答题
    chapter = q["chapter"]
    key = f"{user_id}_{chapter}"
    if key not in quiz_progress_store:
        quiz_progress_store[key] = {"correct": 0, "asked": 0, "last_correct": None}

    progress = quiz_progress_store[key]
    progress["asked"] += 1
    progress["last_correct"] = is_correct
    if is_correct and not is_interest:
        progress["correct"] += 1

    return {
        "success": True,
        "data": {
            "question_id": answer.question_id,
            "is_correct": is_correct,
            "is_interest": is_interest,
            "correct_answer": q["answer"] if not is_interest else None,
            "explanation": q["explanation"],
            "chapter_progress": {
                "correct": progress["correct"],
                "required": CHAPTER_ALLOCATION[chapter]["required"],
                "asked": progress["asked"],
                "total": CHAPTER_ALLOCATION[chapter]["total"]
            }
        }
    }


@router.post("/submit-all-answers/{user_id}")
async def submit_all_answers(user_id: int, request: SubmitQuizRequest):
    """提交全部答案，清除进度缓存"""
    results = []
    correct_count = 0
    interest_answer = None

    for a in request.answers:
        q = get_question(a.question_id)
        if not q:
            continue
        is_interest = q["answer"] == -1
        is_correct = a.selected_option == q["answer"] if not is_interest else True

        results.append({
            "question_id": a.question_id,
            "chapter": q["chapter"],
            "knowledge_points": q["knowledge_points"],
            "selected_option": a.selected_option,
            "is_correct": is_correct,
            "correct_answer": q["answer"] if not is_interest else None,
            "explanation": q["explanation"]
        })

        if is_interest:
            interest_answer = a.selected_option  # 0=NLP, 1=CV, 2=RL, 3=MLOps
        elif is_correct:
            correct_count += 1

    # 清除该用户的进度缓存
    keys_to_del = [k for k in quiz_progress_store if k.startswith(f"{user_id}_")]
    for k in keys_to_del:
        del quiz_progress_store[k]

    return {
        "success": True,
        "data": {
            "total_questions": len(results),
            "correct_count": correct_count,
            "completion_rate": round(correct_count / max(len(results), 1), 2),
            "interest_answer": interest_answer,
            "answers": results
        }
    }


# ===== 阶段 4: 画像生成 =====

class GenerateProfileRequest(BaseModel):
    quiz_answers: List[Dict[str, Any]]
    basic_info: Optional[Dict[str, str]] = None
    learning_goals: Optional[Dict[str, Any]] = None
    prior_experience: Optional[Dict[str, Any]] = None


@router.post("/generate-profile/{user_id}")
async def generate_profile(user_id: int, request: GenerateProfileRequest):
    """综合文档解析 + 答题结果 → 生成完整画像"""
    try:
        async with db_conn._async_session_factory() as db:
            # 获取之前上传的文档解析结果
            result_obj = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result_obj.scalar_one_or_none()

            doc_extracted = None
            if profile and profile.profile_detail:
                uploaded = profile.profile_detail.get("uploaded_document", {})
                if uploaded.get("extracted_info"):
                    doc_extracted = uploaded["extracted_info"]

            # 1. 构建画像详情
            basic_info = request.basic_info or {}
            learning_goals = request.learning_goals or {}
            prior_experience = request.prior_experience or {}

            # 从文档补充信息
            if doc_extracted:
                if not prior_experience.get("courses_taken") and doc_extracted.get("courses_taken"):
                    prior_experience["courses_taken"] = doc_extracted["courses_taken"]
                if not prior_experience.get("projects") and doc_extracted.get("projects"):
                    prior_experience["projects"] = doc_extracted["projects"]
                if not prior_experience.get("self_assessment") and doc_extracted.get("self_assessment"):
                    prior_experience["self_assessment"] = "\n".join(doc_extracted["self_assessment"])

            # 2. 调用规则引擎生成 capability_matrix
            engine_result = profile_engine.build_capability_matrix(
                quiz_answers=request.quiz_answers,
                doc_info=doc_extracted
            )

            # 3. 获取兴趣方向
            interest_answer = None
            for a in request.quiz_answers:
                if a.get("question_id") == "adv_1":
                    interest_answer = a.get("selected_option")
                    break

            advanced_interest = {}
            for i, field in enumerate(["nlp", "cv", "reinforcement_learning", "mlops"]):
                advanced_interest[field] = (interest_answer == i) if interest_answer is not None else False

            # 4. 组装完整画像
            profile_detail = {
                "basic_info": basic_info,
                "learning_goals": learning_goals,
                "prior_experience": prior_experience,
                "uploaded_document": profile.profile_detail.get("uploaded_document") if profile else None,
                "quiz_result": {
                    "total_questions": len(request.quiz_answers),
                    "correct_count": sum(1 for a in request.quiz_answers if a.get("is_correct")),
                    "completion_rate": engine_result["quiz_completeness"]
                },
                "advanced_interest": advanced_interest
            }

            # 5. 存入数据库
            if not profile:
                profile = StudentProfile(user_id=user_id)
                db.add(profile)

            profile.capability_matrix = engine_result["capability_matrix"]
            profile.overall_score = engine_result["overall_score"]
            profile.confidence_score = engine_result["confidence_score"]
            profile.profile_version = (profile.profile_version or 0) + 1
            profile.profile_detail = profile_detail
            profile.major = basic_info.get("major") or profile.major
            profile.grade_level = basic_info.get("grade") or profile.grade_level
            profile.preferred_language = basic_info.get("preferred_language") or profile.preferred_language

            await db.commit()

            # 6. 缓存到 Redis（异步调用）
            try:
                await CacheService.cache_profile(user_id, {
                    "capability_matrix": engine_result["capability_matrix"],
                    "overall_score": engine_result["overall_score"],
                    "confidence_score": engine_result["confidence_score"],
                    "profile_detail": profile_detail
                })
            except Exception as cache_err:
                logger.warning(f"[Wizard] Redis缓存写入失败（不影响功能）: {cache_err}")

            weak_points = profile_engine.get_weak_points(engine_result["capability_matrix"])
            strong_points = profile_engine.get_strong_points(engine_result["capability_matrix"])

            return {
                "success": True,
                "data": {
                    "capability_matrix": engine_result["capability_matrix"],
                    "overall_score": engine_result["overall_score"],
                    "confidence_score": engine_result["confidence_score"],
                    "profile_detail": profile_detail,
                    "weak_points": weak_points,
                    "strong_points": strong_points,
                    "profile_version": profile.profile_version
                }
            }
    except Exception as e:
        logger.error(f"[Wizard] 生成画像失败: {e}", exc_info=True)
        raise HTTPException(500, f"画像生成失败: {str(e)}")


# ===== 前端向导直接保存画像（使用前端计算的能力矩阵） =====

class SaveComputedProfileRequest(BaseModel):
    capability_matrix: Dict[str, int]  # { 章节名: 分数(0-100) }
    quiz_answers: Optional[List[Dict[str, Any]]] = None


@router.post("/save-computed-profile/{user_id}")
async def save_computed_profile(user_id: int, request: SaveComputedProfileRequest):
    """接收前端向导已计算的 capability_matrix 并存入数据库"""
    try:
        async with db_conn._async_session_factory() as db:
            result_obj = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result_obj.scalar_one_or_none()

            # 将 0-100 分数映射为 capability_matrix 格式
            frontend_matrix = request.capability_matrix
            scores = list(frontend_matrix.values())
            overall_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0
            confidence_score = 0.5

            # 转换为后端格式（兼容 full-profile 读取）
            capability_matrix = {}
            for ch_name, score in frontend_matrix.items():
                # 将 0-100 分数映射到 1-5 分
                mapped_score = round(max(1.0, min(5.0, score / 20)), 1)
                capability_matrix[ch_name] = {
                    "章节掌握度": {
                        "score": mapped_score,
                        "confidence": confidence_score,
                        "notes": f"基于15题测评结果，章节得分 {score}/100"
                    }
                }

            # 存入数据库
            if not profile:
                profile = StudentProfile(user_id=user_id)
                db.add(profile)

            profile.capability_matrix = capability_matrix
            profile.overall_score = overall_score
            profile.confidence_score = confidence_score
            profile.profile_version = (profile.profile_version or 0) + 1
            profile.profile_detail = {
                **(dict(profile.profile_detail or {})),
                "quiz_result": {
                    "total_questions": len(request.quiz_answers) if request.quiz_answers else 15,
                    "completion_rate": 1.0
                }
            }

            await db.commit()

            logger.info(f"[Wizard] 前端计算画像已保存: user_id={user_id}, overall={overall_score}")

            return {
                "success": True,
                "data": {
                    "overall_score": overall_score,
                    "confidence_score": confidence_score,
                    "profile_version": profile.profile_version
                }
            }
    except Exception as e:
        logger.error(f"[Wizard] 保存画像失败: {e}", exc_info=True)
        raise HTTPException(500, f"画像保存失败: {str(e)}")


# ===== 阶段 5: 画像确认与微调 =====

@router.post("/confirm-profile/{user_id}")
async def confirm_profile(user_id: int, request: ProfileConfirmRequest):
    """用户确认画像，支持手动微调"""
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        if not profile:
            raise HTTPException(404, "画像不存在，请先生成")

        # 应用微调
        if request.adjustments:
            matrix = profile.capability_matrix or {}
            for chapter, kps in request.adjustments.items():
                if chapter in matrix and isinstance(kps, dict):
                    for kp_name, adjustment in kps.items():
                        if kp_name in matrix[chapter] and isinstance(adjustment, (int, float)):
                            old = matrix[chapter][kp_name]["score"]
                            matrix[chapter][kp_name]["score"] = max(1.0, min(5.0, old + adjustment))
                            matrix[chapter][kp_name]["notes"] = (
                                matrix[chapter][kp_name].get("notes", "") +
                                f" (用户手动调整 {adjustment:+d})"
                            )
            profile.capability_matrix = matrix

        # 添加备注
        if request.notes:
            existing_detail = profile.profile_detail or {}
            existing_detail["user_notes"] = request.notes
            profile.profile_detail = existing_detail

        profile.profile_version = (profile.profile_version or 0) + 1
        await db.commit()

        return {
            "success": True,
            "message": "画像已确认",
            "data": {
                "capability_matrix": profile.capability_matrix,
                "overall_score": profile.overall_score,
                "profile_version": profile.profile_version
            }
        }


# ===== 阶段 6: 获取弱项知识点（供后续学习资料生成）=====

@router.get("/weak-points/{user_id}")
async def get_weak_points(user_id: int, threshold: float = 2.5):
    """获取薄弱知识点列表（score ≤ threshold），驱动学习资料生成"""
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        if not profile or not profile.capability_matrix:
            return {"success": True, "data": {"weak_points": [], "message": "画像未生成"}}

        weak_points = profile_engine.get_weak_points(profile.capability_matrix, threshold)
        strong_points = profile_engine.get_strong_points(profile.capability_matrix)

        return {
            "success": True,
            "data": {
                "weak_points": weak_points,
                "strong_points": strong_points,
                "overall_score": profile.overall_score,
                "total_weak": len(weak_points),
                "recommendation": "系统将基于薄弱知识点生成个性化学习资料"
            }
        }


# ===== 获取完整画像 =====

@router.get("/full-profile/{user_id}")
async def get_full_profile(user_id: int):
    """获取完整画像数据（用于前端展示雷达图/热力图）"""
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        if not profile:
            return {"success": True, "data": None, "message": "画像不存在"}

        chapter_names = get_chapter_names()

        # 计算章节级汇总
        chapter_summary = {}
        capability_matrix_array = []

        if profile.capability_matrix:
            for ch_id, kps in profile.capability_matrix.items():
                if isinstance(kps, dict) and kps:
                    # 提取知识点分数
                    kp_list = []
                    for kp_name, kp_data in kps.items():
                        if isinstance(kp_data, dict) and "score" in kp_data:
                            kp_list.append({
                                "name": kp_name,
                                "score": kp_data["score"],
                                "confidence": kp_data.get("confidence", 0.5)
                            })

                    avg = round(sum(k["score"] for k in kp_list) / len(kp_list), 1) if kp_list else 0

                    chapter_summary[ch_id] = {
                        "name": chapter_names.get(ch_id, ch_id),
                        "avg_score": avg,
                        "knowledge_points": kps
                    }

                    capability_matrix_array.append({
                        "chapter_name": chapter_names.get(ch_id, ch_id),
                        "avg_score": avg,
                        "knowledge_points": kp_list
                    })

        # 合并 basic_info：优先 profile_detail 中的，兜底用数据库字段
        basic_info = (profile.profile_detail or {}).get("basic_info", {})
        if isinstance(basic_info, dict):
            basic_info = dict(basic_info)
        else:
            basic_info = {}
        if not basic_info.get("major") and profile.major:
            basic_info["major"] = profile.major
        if not basic_info.get("grade") and profile.grade_level:
            basic_info["grade"] = profile.grade_level
        if not basic_info.get("preferred_language") and profile.preferred_language:
            basic_info["preferred_language"] = profile.preferred_language

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "basic_info": basic_info,
                "learning_goals": (profile.profile_detail or {}).get("learning_goals", {}),
                "prior_experience": (profile.profile_detail or {}).get("prior_experience", {}),
                "capability_matrix": profile.capability_matrix,
                "capability_matrix_array": capability_matrix_array,
                "chapter_summary": chapter_summary,
                "overall_score": profile.overall_score,
                "confidence_score": profile.confidence_score,
                "profile_version": profile.profile_version,
                "created_at": str(profile.created_at) if profile.created_at else None,
                "updated_at": str(profile.updated_at) if profile.updated_at else None
            }
        }


# ===== 对话式画像构建（无文档上传时使用）=====

class ChatProfileMessage(BaseModel):
    content: str


class ChatProfileRequest(BaseModel):
    messages: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]


@router.post("/chat-profile/{user_id}")
async def chat_profile(user_id: int, request: ChatProfileRequest):
    """对话式画像构建：通过自然语言对话提取学生特征（≥6维度）

    当用户没有上传文档时，通过此接口与画像构建Agent对话，
    Agent会引导用户提供专业、年级、知识基础、学习风格、目标等信息
    """
    from services.llm_service import get_llm_service

    llm = await get_llm_service()

    conversation = request.messages

    profile_context = ""
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()
        if profile:
            existing = {}
            if profile.major:
                existing["major"] = profile.major
            if profile.grade_level:
                existing["grade_level"] = profile.grade_level
            if profile.target_role:
                existing["target_role"] = profile.target_role
            if profile.prior_courses:
                existing["prior_courses"] = profile.prior_courses
            if profile.skill_matrix:
                existing["skill_matrix"] = profile.skill_matrix
            if profile.cognitive_profile:
                existing["cognitive_profile"] = profile.cognitive_profile
            if profile.motivation_profile:
                existing["motivation_profile"] = profile.motivation_profile
            if existing:
                profile_context = f"\n【已收集的画像数据】：{json.dumps(existing, ensure_ascii=False)}\n"

    system_prompt = f"""你是机器学习学生画像构建助手。你的任务是通过友好的对话方式，逐步了解学生的学习背景。
{profile_context}
你需要收集以下 6 大类信息（≥6 维度）：
1. 基础档案：专业、年级、目标职业
2. 技能水平：数学基础（线性代数、概率、微积分等）、编程能力（Python、NumPy、Pandas等）、机器学习知识（监督学习、深度学习、NLP、CV等）
3. 已修课程和项目经历
4. 学习风格偏好（视觉型/听觉型/阅读型/实践型）
5. 学习目标（找工作/科研/转行/兴趣）
6. 薄弱点和困惑

对话策略：
- 每次只问 1-2 个问题，不要一口气问太多
- 根据对方的回答自然地引导到下一个话题
- 用友好的语气，让学生感到舒适
- 如果学生已经提供了一些信息，就跳过那些话题
- 每轮回复控制在 3-5 句话内
- 如果已经收集了足够信息（专业+年级+至少3个技能维度+目标），在回复末尾加上 [PROFILE_READY]

对话历史：
"""
    for msg in conversation:
        role = "学生" if msg["role"] == "user" else "助手"
        system_prompt += f"{role}: {msg['content']}\n"

    system_prompt += "\n请继续对话，根据已收集的信息进行下一步引导。"

    try:
        result = await llm.chat(
            messages=[{"role": "user", "content": "（请根据对话历史和已收集的信息，继续引导对话收集画像数据）"}],
            system_prompt=system_prompt,
            temperature=0.7
        )
        reply = result.get("content", "")
        profile_ready = "[PROFILE_READY]" in reply
        reply = reply.replace("[PROFILE_READY]", "").strip()

        return {
            "success": True,
            "data": {
                "reply": reply,
                "profile_ready": profile_ready,
                "tokens_used": result.get("tokens_used", 0)
            }
        }
    except Exception as e:
        logger.error(f"[Wizard] 对话画像失败: {e}")
        raise HTTPException(500, f"对话画像失败: {str(e)}")


@router.post("/generate-chat-profile/{user_id}")
async def generate_chat_profile(user_id: int, request: ChatProfileRequest):
    """基于对话历史生成完整结构化画像"""
    from services.llm_service import get_llm_service

    llm = await get_llm_service()

    conversation_text = ""
    for msg in request.messages:
        role = "学生" if msg["role"] == "user" else "助手"
        conversation_text += f"{role}: {msg['content']}\n"

    prompt = f"""你是机器学习教育画像分析专家。请从以下对话中提取完整的学生画像。

【对话内容】：
{conversation_text}

返回纯 JSON（不要用 markdown 代码块包裹）："""

    prompt += r"""
{
  "major": "专业名称",
  "grade_level": "大一/大二/大三/大四/研一/研二/研三/已工作",
  "target_role": "目标职业",
  "prior_courses": ["课程1"],
  "preferred_language": "Python/R",

  "skill_matrix": {
    "math": {"linear_algebra": 1-5, "probability": 1-5, "calculus": 1-5, "statistics": 1-5, "optimization": 1-5},
    "programming": {"python": 1-5, "numpy": 1-5, "pandas": 1-5, "data_structure": 1-5, "algorithm": 1-5, "sql": 1-5},
    "machine_learning": {"supervised": 1-5, "unsupervised": 1-5, "neural_networks": 1-5, "deep_learning": 1-5, "nlp": 1-5, "cv": 1-5, "reinforcement": 1-5, "feature_engineering": 1-5, "model_evaluation": 1-5, "mlops": 1-5, "ensemble_methods": 1-5},
    "tools": {"sklearn": 1-5, "pytorch": 1-5, "tensorflow": 1-5, "jupyter": 1-5, "git": 1-5, "docker": 1-5, "matplotlib": 1-5, "mlflow": 1-5}
  },

  "cognitive_profile": {
    "bloom_level": "remember/understand/apply/analyze/evaluate/create",
    "learning_style": "visual/auditory/reading/kinesthetic",
    "abstraction_ability": 1-5,
    "mathematical_maturity": 1-5,
    "learning_pace": "slow/medium/fast",
    "prefers_theory_first": true/false,
    "needs_concrete_examples": true/false
  },

  "motivation_profile": {
    "primary_motivation": "job_hunting/research/career_change/curiosity/exam",
    "urgency_level": 1-5,
    "self_efficacy": 1-5,
    "topic_passion": [{"topic": "主题", "interest": 0.0-1.0}],
    "career_target": "目标岗位"
  },

  "behavior_pattern": {
    "avg_session_minutes": 45,
    "content_format_preference": ["document", "code"],
    "exercise_type_preference": "coding",
    "persistence_score": 3
  },

  "confidence_score": 0.0-1.0
}

要求：
1. 从对话中尽可能提取信息，不确定的维度给保守值（不要给null）
2. skill_matrix 中，说"学过"给3分，"掌握"给4分，"精通"给5分，"了解"给2分
3. confidence_score 表示你对提取结果的信心
"""

    try:
        result = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是机器学习教育画像分析专家。从对话中提取学生特征。返回纯JSON。",
            temperature=0.2
        )
        content = result.get("content", "")
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            if content.startswith("json"):
                content = content[4:].strip()

        profile_data = json.loads(content)

        async with db_conn._async_session_factory() as db:
            result_obj = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result_obj.scalar_one_or_none()
            if not profile:
                profile = StudentProfile(user_id=user_id)
                db.add(profile)

            existing_detail = dict(profile.profile_detail or {})
            existing_detail["pending_profile_data"] = profile_data
            existing_detail["pending_profile_source"] = "chat"
            existing_detail["pending_profile_at"] = datetime.now().isoformat()

            existing_detail["basic_info"] = {
                "major": profile_data.get("major") or "",
                "grade": profile_data.get("grade_level") or "",
                "preferred_language": profile_data.get("preferred_language") or ""
            }
            existing_detail["learning_goals"] = {
                "target_role": profile_data.get("target_role") or "",
                "motivation": (profile_data.get("motivation_profile") or {}).get("primary_motivation") or ""
            }

            if profile_data.get("major"):
                profile.major = profile_data["major"]
            if profile_data.get("grade_level"):
                profile.grade_level = profile_data["grade_level"]
            if profile_data.get("target_role"):
                profile.target_role = profile_data["target_role"]
            if profile_data.get("preferred_language"):
                profile.preferred_language = profile_data["preferred_language"]
            if profile_data.get("prior_courses"):
                profile.prior_courses = profile_data["prior_courses"]

            profile.profile_detail = existing_detail
            await db.commit()

        return {
            "success": True,
            "data": {
                "profile": profile_data,
                "confidence_score": profile_data.get("confidence_score", 0)
            }
        }
    except Exception as e:
        logger.error(f"[Wizard] 生成对话画像失败: {e}")
        raise HTTPException(500, f"生成画像失败: {str(e)}")


@router.get("/profile-llm-extracted/{user_id}")
async def get_profile_llm_extracted(user_id: int):
    """获取 LLM 画像构建Agent提取的最新画像数据"""
    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        if not profile:
            return {"success": True, "data": None, "message": "画像不存在"}

        llm_extracted = (profile.profile_detail or {}).get("llm_extracted")

        return {
            "success": True,
            "data": {
                "major": profile.major,
                "grade_level": profile.grade_level,
                "target_role": profile.target_role,
                "prior_courses": profile.prior_courses,
                "preferred_language": profile.preferred_language,
                "skill_matrix": profile.skill_matrix,
                "cognitive_profile": profile.cognitive_profile,
                "motivation_profile": profile.motivation_profile,
                "misconception_archive": profile.misconception_archive,
                "behavior_pattern": profile.behavior_pattern,
                "profile_version": profile.profile_version,
                "llm_extracted": llm_extracted
            }
        }


class CombineProfileRequest(BaseModel):
    capability_matrix: Dict[str, int]  # 测评得分 {"线性回归": 80, ...}
    quiz_answers: List[QuizAnswer]


@router.post("/combine-and-generate-profile/{user_id}")
async def combine_and_generate_profile(user_id: int, request: CombineProfileRequest):
    """Stage 5 画像生成：合并测评结果 + 暂存的文档/对话画像数据，生成完整画像

    在用户完成能力测评后调用此端点，将测评的 capability_matrix
    与之前暂存的 pending_profile_data 合并，通过LLM生成完整结构化画像
    """
    from services.llm_service import get_llm_service

    async with db_conn._async_session_factory() as db:
        result_obj = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result_obj.scalar_one_or_none()

        if not profile:
            profile = StudentProfile(user_id=user_id)
            db.add(profile)

        pd = dict(profile.profile_detail or {})
        pending = pd.pop("pending_profile_data", None)
        pending_source = pd.pop("pending_profile_source", "none")

        scores_text = json.dumps(request.capability_matrix, ensure_ascii=False)
        pending_text = json.dumps(pending, ensure_ascii=False) if pending else "无暂存数据"

        llm = await get_llm_service()

        prompt = f"""你是机器学习教育画像分析专家。请合并以下两方面的数据，生成一个完整的学生画像。

【能力测评结果（基于 15 道题）】：
{scores_text}

【暂存画像数据（来源: {pending_source}）】：
{pending_text}

请综合两份数据，返回纯 JSON（不要用 markdown 代码块包裹）："""

        prompt += r"""
{
  "major": "专业名称",
  "grade_level": "大一/大二/大三/大四/研一/研二/研三/已工作",
  "target_role": "目标职业",
  "prior_courses": ["课程1"],
  "preferred_language": "Python/R",

  "skill_matrix": {
    "math": {"linear_algebra": 1-5, "probability": 1-5, "calculus": 1-5, "statistics": 1-5, "optimization": 1-5},
    "programming": {"python": 1-5, "numpy": 1-5, "pandas": 1-5, "data_structure": 1-5, "algorithm": 1-5, "sql": 1-5},
    "machine_learning": {"supervised": 1-5, "unsupervised": 1-5, "neural_networks": 1-5, "deep_learning": 1-5, "nlp": 1-5, "cv": 1-5, "reinforcement": 1-5, "feature_engineering": 1-5, "model_evaluation": 1-5, "mlops": 1-5, "ensemble_methods": 1-5},
    "tools": {"sklearn": 1-5, "pytorch": 1-5, "tensorflow": 1-5, "jupyter": 1-5, "git": 1-5, "docker": 1-5, "matplotlib": 1-5, "mlflow": 1-5}
  },

  "cognitive_profile": {
    "bloom_level": "remember/understand/apply/analyze/evaluate/create",
    "learning_style": "visual/auditory/reading/kinesthetic",
    "abstraction_ability": 1-5,
    "mathematical_maturity": 1-5,
    "learning_pace": "slow/medium/fast",
    "prefers_theory_first": true/false,
    "needs_concrete_examples": true/false
  },

  "motivation_profile": {
    "primary_motivation": "job_hunting/research/career_change/curiosity/exam",
    "urgency_level": 1-5,
    "self_efficacy": 1-5,
    "topic_passion": [{"topic": "主题", "interest": 0.0-1.0}],
    "career_target": "目标岗位"
  },

  "overall_score": 0-100,
  "confidence_score": 0.0-1.0
}

要求：
1. 优先使用暂存画像数据中的 personal info（专业、年级、目标）
2. skill_matrix 结合测评结果和暂存数据
3. overall_score 基于测评的 capability_matrix 计算均分
4. 暂存数据中的认知画像、动机画像直接使用（这些测评是测不出来的）
5. 如果暂存数据中 target_role 为空，根据测评得分分布推断：高分章节多的偏向"算法工程师"，均衡的偏向"数据分析师"
6. 如果暂存数据中 motivation_profile.primary_motivation 为空，根据测评表现推断：主动做测评 → "curiosity"，得分高 → "job_hunting"
7. 即使暂存数据中某些字段为空，也要给出合理的推断值，不要返回 null 或空字符串
"""

        try:
            result = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是机器学习教育画像分析专家。合并测评结果和暂存数据生成完整画像。返回纯JSON。",
                temperature=0.3
            )
            content = result.get("content", "")
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                if content.startswith("json"):
                    content = content[4:].strip()

            combined = json.loads(content)

            _apply_profile_extraction(profile, combined)

            pd["basic_info"] = {
                "major": combined.get("major") or pd.get("basic_info", {}).get("major", ""),
                "grade": combined.get("grade_level") or pd.get("basic_info", {}).get("grade", ""),
                "preferred_language": combined.get("preferred_language") or pd.get("basic_info", {}).get("preferred_language", "")
            }
            pd["learning_goals"] = {
                "target_role": combined.get("target_role") or pd.get("learning_goals", {}).get("target_role", ""),
                "motivation": (combined.get("motivation_profile") or {}).get("primary_motivation") or pd.get("learning_goals", {}).get("motivation", "")
            }
            if combined.get("prior_courses"):
                pd["prior_experience"] = pd.get("prior_experience", {})
                pd["prior_experience"]["courses_taken"] = combined["prior_courses"]

            profile.profile_detail = pd

            scores_list = list(request.capability_matrix.values())
            combined["overall_score"] = combined.get("overall_score") or (
                round(sum(scores_list) / max(len(scores_list), 1), 1) if scores_list else 0
            )

            capability_matrix = {}
            for ch_name, score in request.capability_matrix.items():
                mapped_score = round(max(1.0, min(5.0, score / 20)), 1)
                capability_matrix[ch_name] = {
                    "章节掌握度": {
                        "score": mapped_score,
                        "confidence": combined.get("confidence_score", 0.5),
                        "notes": f"基于测评得分 {score}/100，结合暂存画像数据"
                    }
                }
            profile.capability_matrix = capability_matrix
            profile.overall_score = combined.get("overall_score", 0)
            profile.confidence_score = combined.get("confidence_score", 0.5)
            profile.profile_version = (profile.profile_version or 0) + 1

            await db.commit()

            logger.info(f"[Wizard] 合并画像生成完成: user_id={user_id}, source={pending_source}")

            return {
                "success": True,
                "data": {
                    "profile": combined,
                    "overall_score": profile.overall_score,
                    "confidence_score": profile.confidence_score,
                    "profile_version": profile.profile_version,
                    "pending_source": pending_source
                }
            }
        except Exception as e:
            logger.error(f"[Wizard] 合并画像生成失败: {e}")
            raise HTTPException(500, f"合并画像生成失败: {str(e)}")