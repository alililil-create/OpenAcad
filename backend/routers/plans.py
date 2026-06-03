from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_session_factory
from services.plan_service import (
    create_plan, get_active_plan, get_plan_tasks, complete_task,
    adjust_plan, get_weekly_schedule, get_goal_config, GOAL_CONFIG
)
from services.knowledge_graph import KNOWLEDGE_GRAPH

router = APIRouter(prefix="/api/plans", tags=["plans"])


class CreatePlanRequest(BaseModel):
    user_id: int
    goal_type: str
    goal_detail: Optional[str] = None
    deadline: Optional[str] = None
    weekly_hours: float = 10.0
    target_chapters: Optional[List[str]] = None


class CompleteTaskRequest(BaseModel):
    result_data: Optional[dict] = None


@router.get("/goals")
async def list_goals():
    return {"success": True, "data": {k: {"label": v["label"], "desc": v["desc"], "default_weeks": v["default_weeks"], "focus": v["focus"]} for k, v in GOAL_CONFIG.items()}}


@router.get("/chapters")
async def list_chapters():
    chapters = []
    for ch_id, ch in KNOWLEDGE_GRAPH.items():
        chapters.append({
            "id": ch_id, "name": ch["name"], "icon": ch.get("icon", "📌"),
            "difficulty": ch.get("difficulty", 3), "estimated_hours": ch.get("estimated_hours", 0),
            "depends_on": ch.get("depends_on", []),
        })
    return {"success": True, "data": chapters}


@router.post("/create")
async def api_create_plan(req: CreatePlanRequest):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        deadline = None
        if req.deadline:
            try:
                deadline = datetime.fromisoformat(req.deadline)
            except:
                pass
        plan = await create_plan(db, req.user_id, req.goal_type, req.goal_detail, deadline, req.weekly_hours, req.target_chapters)
        tasks = await get_plan_tasks(db, plan.id)
        return {"success": True, "data": {
            "id": plan.id, "goal_type": plan.goal_type, "goal_detail": plan.goal_detail,
            "deadline": str(plan.deadline) if plan.deadline else None,
            "chapter_ids": plan.chapter_ids, "schedule": plan.schedule,
            "progress_pct": plan.progress_pct, "status": plan.status,
            "tasks": [
                {"id": t.id, "chapter_id": t.chapter_id, "task_type": t.task_type,
                 "task_date": str(t.task_date) if t.task_date else None,
                 "duration_min": t.duration_min, "status": t.status, "order_index": t.order_index,
                 "result": t.result}
                for t in tasks
            ],
        }}


@router.get("/active/{user_id}")
async def api_get_active_plan(user_id: int):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        plan = await get_active_plan(db, user_id)
        if not plan:
            return {"success": True, "data": None}
        tasks = await get_plan_tasks(db, plan.id)
        return {"success": True, "data": {
            "id": plan.id, "goal_type": plan.goal_type, "goal_detail": plan.goal_detail,
            "deadline": str(plan.deadline) if plan.deadline else None,
            "chapter_ids": plan.chapter_ids, "schedule": plan.schedule,
            "progress_pct": plan.progress_pct, "status": plan.status,
            "tasks": [
                {"id": t.id, "chapter_id": t.chapter_id, "task_type": t.task_type,
                 "task_date": str(t.task_date) if t.task_date else None,
                 "duration_min": t.duration_min, "status": t.status, "order_index": t.order_index,
                 "result": t.result}
                for t in tasks
            ],
        }}


@router.post("/task/{task_id}/complete")
async def api_complete_task(task_id: int, req: CompleteTaskRequest = None):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        task = await complete_task(db, task_id, req.result_data if req else None)
        if not task:
            raise HTTPException(404, "任务不存在")
        return {"success": True, "data": {"id": task.id, "status": task.status}}


@router.get("/weekly/{user_id}")
async def api_weekly_schedule(user_id: int):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        tasks = await get_weekly_schedule(db, user_id)
        return {"success": True, "data": tasks}


@router.post("/adjust/{plan_id}")
async def api_adjust_plan(plan_id: int):
    sf = get_session_factory()
    if not sf:
        raise HTTPException(500, "数据库未初始化")
    async with sf() as db:
        plan = await adjust_plan(db, plan_id, {})
        if not plan:
            raise HTTPException(404, "计划不存在")
        return {"success": True, "data": {"id": plan.id, "schedule": plan.schedule, "progress_pct": plan.progress_pct}}
