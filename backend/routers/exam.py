from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_session_factory
from services.exam_service import (
    create_exam, get_exam, submit_exam, get_user_exams,
    EXAM_TYPE_CONFIG
)
from database.models import ExamPaper

router = APIRouter(prefix="/api/exam", tags=["exam"])


class CreateExamRequest(BaseModel):
    user_id: int
    exam_type: str
    chapter_ids: List[str]


class SubmitExamRequest(BaseModel):
    answers: List
    time_spent_sec: int = 0


@router.get("/types")
async def list_exam_types():
    return {"success": True, "data": {k: {"label": v["label"], "time_min": v["time_min"]} for k, v in EXAM_TYPE_CONFIG.items()}}


@router.post("/create")
async def api_create_exam(req: CreateExamRequest):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        exam = await create_exam(db, req.user_id, req.exam_type, req.chapter_ids)
        return {"success": True, "data": {
            "id": exam.id, "exam_type": exam.exam_type,
            "chapter_ids": exam.chapter_ids, "questions": exam.questions,
            "time_limit_min": exam.time_limit_min, "total_score": exam.total_score,
            "status": exam.status,
        }}


@router.get("/{exam_id}")
async def api_get_exam(exam_id: int):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        exam = await get_exam(db, exam_id)
        if not exam:
            raise HTTPException(404, "试卷不存在")
        resp = {
            "id": exam.id, "exam_type": exam.exam_type,
            "chapter_ids": exam.chapter_ids, "questions": exam.questions,
            "time_limit_min": exam.time_limit_min, "total_score": exam.total_score,
            "status": exam.status,
        }
        if exam.status == "completed":
            resp["answers"] = exam.answers
            resp["score"] = exam.score
            resp["time_spent_sec"] = exam.time_spent_sec
        return {"success": True, "data": resp}


@router.post("/{exam_id}/submit")
async def api_submit_exam(exam_id: int, req: SubmitExamRequest):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        result = await submit_exam(db, exam_id, req.answers, req.time_spent_sec)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return {"success": True, "data": result}


@router.get("/list/{user_id}")
async def api_list_exams(user_id: int, exam_type: Optional[str] = None):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id 无效")
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        exams = await get_user_exams(db, user_id, exam_type)
        return {"success": True, "data": [
            {
                "id": e.id, "exam_type": e.exam_type, "chapter_ids": e.chapter_ids,
                "score": e.score, "total_score": e.total_score,
                "status": e.status, "time_limit_min": e.time_limit_min,
                "created_at": str(e.created_at),
            }
            for e in exams
        ]}
