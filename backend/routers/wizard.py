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


# ===== 阶段 1: 文档上传 =====

@router.post("/upload-document/{user_id}")
async def upload_document(user_id: int, file: UploadFile = File(...)):
    """上传学习背景文档并解析"""
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

    return {
        "success": True,
        "data": {
            "format": result["format"],
            "char_count": result["char_count"],
            "extracted_info": result["extracted_info"]
        }
    }


# ===== 阶段 2: 获取学科列表 + 章节信息 =====

@router.get("/subjects")
async def get_subjects():
    """获取可选学科列表"""
    return {
        "success": True,
        "data": {
            "subjects": [
                {"id": "machine_learning", "name": "机器学习", "chapters": 7, "knowledge_points": 28}
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