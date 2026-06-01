from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
import asyncio
import logging
from datetime import datetime, timedelta

from config import settings
import hashlib
import os
from jose import jwt, JWTError

from database.connection import init_db, close_db, init_redis, close_redis
import database.connection as db_conn
from database.models import User, StudentProfile, LearningResource, LearningProgress, ChatSession
from graph.workflow import execute_workflow
from services.cache_service import CacheService
from services.vector_service import init_milvus, close_milvus, insert_resource, search_resources, rebuild_vocabulary
from services.oss_service import init_minio, close_minio, upload_file, upload_text, get_file, get_presigned_url
from services.video_service import generate_video, test_connectivity, generate_video_script, generate_lecture_script
from services.video_provider import get_provider, get_all_providers
from routers.wizard import router as wizard_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 密码加密 - 使用 hashlib SHA256 避免 bcrypt 版本兼容问题

def hash_password(password: str) -> str:
    """SHA256 + salt 密码哈希"""
    salt = os.urandom(16).hex()
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    try:
        salt, stored_hash = hashed.split("$", 1)
        h = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
        return h == stored_hash
    except ValueError:
        return False


# ===== 应用生命周期 =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    logger.info("[App] 正在初始化数据库...")
    db_url = get_build_db_url()
    logger.info(f"[App] 数据库: {db_url.split('@')[-1] if '@' in db_url else db_url[:50]}")
    await init_db(db_url)

    # Redis 缓存
    if settings.REDIS_ENABLED:
        await init_redis(settings.REDIS_URL)

    # Milvus 向量数据库
    if settings.MILVUS_ENABLED:
        try:
            await init_milvus(settings.MILVUS_URI)
            await rebuild_vocabulary()
        except Exception as e:
            logger.warning(f"[App] Milvus 初始化失败（不影响核心功能）: {e}")

    # MinIO OSS
    if settings.MINIO_ENABLED:
        try:
            await init_minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
        except Exception as e:
            logger.warning(f"[App] MinIO 初始化失败（不影响核心功能）: {e}")

    logger.info("[App] 初始化完成")
    yield
    # 关闭时清理
    await close_db()
    if settings.REDIS_ENABLED:
        await close_redis()
    await close_milvus()
    await close_minio()
    logger.info("[App] 已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="基于LangGraph的多智能体个性化学习系统",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wizard_router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "bei"


# ===== 工具函数 =====

def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_build_db_url() -> str:
    """根据 DB_ENGINE 构建PostgreSQL连接字符串"""
    if settings.DB_ENGINE == "postgresql":
        return (
            f"postgresql+asyncpg://{settings.PG_USER}:{settings.PG_PASSWORD}"
            f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DATABASE}"
        )
    return settings.DATABASE_URL


async def get_db() -> AsyncSession:
    if db_conn._async_session_factory is None:
        raise RuntimeError("数据库未初始化")
    async with db_conn._async_session_factory() as session:
        yield session


# ===== 数据模型 =====

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    thread_id: str = "default"
    user_id: Optional[int] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdate(BaseModel):
    major: Optional[str] = None
    grade_level: Optional[str] = None
    math_foundation: Optional[float] = None
    programming_exp: Optional[float] = None
    ml_knowledge: Optional[float] = None
    learning_style: Optional[str] = None
    learning_goal: Optional[str] = None
    weak_points: Optional[list] = None
    weekly_hours: Optional[float] = None
    interests: Optional[list] = None
    preferred_language: Optional[str] = None


# ===== 前端页面路由 =====

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index():
    path = FRONTEND_DIR / "index.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/profile.html", response_class=HTMLResponse)
async def serve_profile():
    path = FRONTEND_DIR / "profile.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/register.html", response_class=HTMLResponse)
async def serve_register():
    path = FRONTEND_DIR / "register.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/learning-path.html", response_class=HTMLResponse)
async def serve_learning_path():
    path = FRONTEND_DIR / "learning-path.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/exercises.html", response_class=HTMLResponse)
async def serve_exercises():
    path = FRONTEND_DIR / "exercises.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/wizard.html", response_class=HTMLResponse)
async def serve_wizard():
    path = FRONTEND_DIR / "wizard.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/profile-detail.html", response_class=HTMLResponse)
async def serve_profile_detail():
    path = FRONTEND_DIR / "profile-detail.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/resources.html", response_class=HTMLResponse)
async def serve_resources():
    path = FRONTEND_DIR / "resources.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/report.html", response_class=HTMLResponse)
async def serve_report():
    path = FRONTEND_DIR / "report.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/profile-center.html", response_class=HTMLResponse)
async def serve_profile_center():
    path = FRONTEND_DIR / "profile-center.html"
    return path.read_text(encoding="utf-8") if path.exists() else HTMLResponse("404", status_code=404)


@app.get("/styles/{filename}")
async def serve_styles(filename: str):
    path = FRONTEND_DIR / "styles" / filename
    if path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"), media_type="text/css")
    raise HTTPException(status_code=404)


@app.get("/scripts/{filename}")
async def serve_scripts(filename: str):
    path = FRONTEND_DIR / "scripts" / filename
    if path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"), media_type="application/javascript")
    raise HTTPException(status_code=404)


@app.get("/@vite/client")
async def ignore_vite():
    return HTMLResponse("// empty", media_type="application/javascript")


# ===== 认证 API =====

@app.post("/api/auth/register")
async def api_register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册 - 数据库持久化"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建用户
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 生成 token
    token = create_token(user.id, user.username)

    return {
        "success": True,
        "message": "注册成功",
        "data": {
            "user_id": user.id,
            "username": user.username,
            "token": token
        }
    }


@app.post("/api/auth/login")
async def api_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.username == req.username)
    )
    user = result.unique().scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    token = create_token(user.id, user.username)

    return {
        "success": True,
        "message": "登录成功",
        "data": {
            "user_id": user.id,
            "username": user.username,
            "token": token,
            "has_profile": user.profile is not None
        }
    }


# ===== 画像 API =====

@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    """获取完整学生画像（6大类）"""
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return {"success": True, "data": None, "message": "暂无画像"}

    return {
        "success": True,
        "data": {
            "id": profile.id,
            "user_id": profile.user_id,
            "major": profile.major,
            "grade_level": profile.grade_level,
            "target_role": profile.target_role,
            "prior_courses": profile.prior_courses or [],
            "preferred_language": profile.preferred_language,
            "skill_matrix": profile.skill_matrix or {},
            "cognitive_profile": profile.cognitive_profile or {},
            "misconception_archive": profile.misconception_archive or {},
            "behavior_pattern": profile.behavior_pattern or {},
            "motivation_profile": profile.motivation_profile or {},
            "confidence_score": profile.confidence_score,
            "profile_version": profile.profile_version or 1,
            "created_at": str(profile.created_at) if profile.created_at else None,
            "updated_at": str(profile.updated_at) if profile.updated_at else None
        }
    }


# ===== 学习资源 API =====

@app.get("/api/resources/{user_id}")
async def get_user_resources(
    user_id: int,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取用户的学习资源"""
    query = select(LearningResource).where(LearningResource.user_id == user_id)
    if resource_type:
        query = query.where(LearningResource.resource_type == resource_type)
    query = query.order_by(LearningResource.created_at.desc()).limit(50)

    result = await db.execute(query)
    resources = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "resource_type": r.resource_type,
                "title": r.title,
                "content": r.content,
                "topic": r.topic,
                "difficulty": r.difficulty,
                "created_at": str(r.created_at)
            }
            for r in resources
        ]
    }


# ===== 学习进度 API =====

@app.get("/api/progress/{user_id}")
async def get_progress(user_id: int, db: AsyncSession = Depends(get_db)):
    """获取学习进度"""
    result = await db.execute(
        select(LearningProgress)
        .where(LearningProgress.user_id == user_id)
        .order_by(LearningProgress.stage_index)
    )
    stages = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "stage_name": s.stage_name,
                "stage_index": s.stage_index,
                "progress_pct": s.progress_pct,
                "status": s.status,
                "completed_exercises": s.completed_exercises,
                "total_exercises": s.total_exercises,
                "time_spent_minutes": s.time_spent_minutes
            }
            for s in stages
        ]
    }


# ===== 对话历史 API =====

@app.get("/api/chat/history/{user_id}")
async def get_chat_history(
    user_id: int,
    thread_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取对话历史"""
    query = select(ChatSession).where(ChatSession.user_id == user_id)
    if thread_id:
        query = query.where(ChatSession.thread_id == thread_id)
    query = query.order_by(ChatSession.last_message_at.desc()).limit(20)

    result = await db.execute(query)
    sessions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "thread_id": s.thread_id,
                "messages": s.messages,
                "message_count": s.message_count,
                "created_at": str(s.created_at),
                "last_message_at": str(s.last_message_at)
            }
            for s in sessions
        ]
    }


# ===== 核心 AI 对话 API =====

async def _load_existing_profile(db: AsyncSession, user_id: int) -> dict | None:
    """加载已有画像（Redis 缓存 → DB 兜底）"""
    # 1. 先查 Redis 缓存
    cached = await CacheService.get_cached_profile(user_id)
    if cached:
        logger.info(f"[Context] 画像缓存命中 user_id={user_id}")
        return cached

    # 2. 缓存未命中，查数据库
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        data = {
            "major": profile.major,
            "grade_level": profile.grade_level,
            "target_role": profile.target_role,
            "prior_courses": profile.prior_courses or [],
            "preferred_language": profile.preferred_language,
            "skill_matrix": profile.skill_matrix or {},
            "cognitive_profile": profile.cognitive_profile or {},
            "misconception_archive": profile.misconception_archive or {},
            "behavior_pattern": profile.behavior_pattern or {},
            "motivation_profile": profile.motivation_profile or {},
            "confidence_score": profile.confidence_score or 0.5,
            "profile_version": profile.profile_version or 1
        }
        await CacheService.cache_profile(user_id, data)
        logger.info(f"[Context] 画像从DB加载 user_id={user_id} v{data['profile_version']}")
        return data

    logger.info(f"[Context] 无已有画像 user_id={user_id}")
    return None


async def _load_chat_history(db: AsyncSession, user_id: int, thread_id: str) -> list[dict]:
    """从数据库加载历史对话消息"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.thread_id == thread_id
        ).order_by(ChatSession.last_message_at.desc()).limit(1)
    )
    session = result.scalar_one_or_none()
    if session and session.messages:
        messages = session.messages
        # 只取最近20条，避免 token 爆炸
        recent = messages[-20:] if len(messages) > 20 else messages
        logger.info(f"[Context] 历史消息加载 user_id={user_id} thread={thread_id} count={len(recent)}")
        return recent

    logger.info(f"[Context] 无历史对话 user_id={user_id} thread={thread_id}")
    return []


@app.post("/api/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """非流式 AI 对话（保存到数据库）"""
    try:
        # 1. 合并前端历史 + DB历史
        frontend_history = [{"role": m.role, "content": m.content} for m in request.history]
        db_history = await _load_chat_history(db, request.user_id, request.thread_id) \
            if request.user_id else []
        # DB历史优先（更全），去重后合并
        merged_history = db_history if db_history else frontend_history

        # 2. 加载已有画像
        existing_profile = None
        if request.user_id:
            existing_profile = await _load_existing_profile(db, request.user_id)

        # 3. 执行工作流
        final_state = None
        async for event in execute_workflow(
            user_query=request.message,
            chat_history=merged_history,
            thread_id=request.thread_id,
            existing_profile=existing_profile
        ):
            final_state = event

        node_name = list(final_state.keys())[0] if final_state else ""
        node_output = final_state.get(node_name, {}) if final_state else {}

        # 保存画像到数据库 + Redis缓存
        if request.user_id and node_output.get("student_profile"):
            profile_data = node_output["student_profile"]
            await _save_profile(db, request.user_id, profile_data)
            await CacheService.cache_profile(request.user_id, profile_data)

        # 保存学习资源到数据库
        if request.user_id:
            await _save_resources(db, request.user_id, request.thread_id, node_output)

        # 保存对话会话
        if request.user_id:
            summary = _extract_assistant_summary(node_output)
            await _save_chat_session(db, request.user_id, request.thread_id, merged_history, request.message, summary)

        return {
            "success": True,
            "data": {
                "profile": node_output.get("student_profile"),
                "document": node_output.get("document"),
                "questions": node_output.get("questions"),
                "mindmap": node_output.get("mindmap"),
                "code_examples": node_output.get("code_examples"),
                "learning_path": node_output.get("learning_path"),
                "tutor_response": node_output.get("tutor_response"),
                "summary": node_output.get("final_summary"),
                "execution_log": node_output.get("execution_log", []),
                "errors": node_output.get("errors", [])
            }
        }

    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式 AI 对话（多轮上下文 + 画像优化 + Redis缓存）"""
    async def event_generator():
        db = None
        try:
            # 1. 准备上下文：合并前端历史 + DB历史
            frontend_history = [{"role": m.role, "content": m.content} for m in request.history]

            db_history = []
            existing_profile = None

            if db_conn._async_session_factory and request.user_id:
                async with db_conn._async_session_factory() as db:
                    # 加载数据库历史
                    db_history = await _load_chat_history(db, request.user_id, request.thread_id)
                    # 加载已有画像（Redis缓存 → DB）
                    existing_profile = await _load_existing_profile(db, request.user_id)

            # DB历史优先（更完整），否则用前端历史
            merged_history = db_history if db_history else frontend_history

            logger.info(f"[Stream] user_id={request.user_id} thread={request.thread_id} "
                        f"history_len={len(merged_history)} has_profile={existing_profile is not None}")

            # 2. 执行工作流（注入已有画像 → 优化而非重建）
            if db_conn._async_session_factory and request.user_id:
                async with db_conn._async_session_factory() as db:
                    last_state = {}
                    async for event in execute_workflow(
                        user_query=request.message,
                        chat_history=merged_history,
                        thread_id=request.thread_id,
                        existing_profile=existing_profile
                    ):
                        if not event:
                            continue
                        node_name = list(event.keys())[0]
                        node_output = event.get(node_name, {})
                        last_state = node_output

                        yield f"data: {json.dumps({
                            'type': 'agent_start',
                            'agent': node_name
                        }, ensure_ascii=False)}\n\n"

                        # 流式推送内容片段
                        if isinstance(node_output, dict) and node_output:
                            if node_output.get("student_profile"):
                                yield f"data: {json.dumps({
                                    'type': 'agent_content',
                                    'agent': node_name,
                                    'resource_type': 'profile',
                                    'preview': json.dumps(node_output['student_profile'], ensure_ascii=False)[:300]
                                }, ensure_ascii=False)}\n\n"

                            for key in ['document', 'questions', 'mindmap', 'code_examples']:
                                val = node_output.get(key)
                                if val:
                                    yield f"data: {json.dumps({
                                        'type': 'agent_content',
                                        'agent': node_name,
                                        'resource_type': key,
                                        'preview': str(val)[:200]
                                    }, ensure_ascii=False)}\n\n"

                            if node_output.get("video_result"):
                                v = node_output["video_result"]
                                dur = v.get("duration", 0)
                                res = v.get("resolution", "720p")
                                vu = v.get("url", "")
                                yield "data: " + json.dumps({
                                    "type": "agent_content",
                                    "agent": node_name,
                                    "resource_type": "video",
                                    "preview": "教学视频已生成 ({}s, {})".format(dur, res),
                                    "video_url": vu,
                                }, ensure_ascii=False) + "\n\n"

                        yield f"data: {json.dumps({
                            'type': 'agent_complete',
                            'agent': node_name,
                            'status': 'success'
                        }, ensure_ascii=False)}\n\n"

                        await asyncio.sleep(0.1)

                    # 3. 持久化：画像 → DB + Redis，对话 → DB
                    if last_state.get("student_profile"):
                        await _save_profile(db, request.user_id, last_state["student_profile"])
                        await CacheService.cache_profile(request.user_id, last_state["student_profile"])
                        logger.info(f"[Stream] 画像已保存+缓存 user_id={request.user_id}")

                    summary = _extract_assistant_summary(last_state)
                    await _save_chat_session(db, request.user_id, request.thread_id, merged_history, request.message, summary)
                    logger.info(f"[Stream] 会话已保存 user_id={request.user_id} thread={request.thread_id}")

            else:
                # 无 user_id，只运行工作流不存数据库
                async for event in execute_workflow(
                    user_query=request.message,
                    chat_history=merged_history,
                    thread_id=request.thread_id,
                    existing_profile=existing_profile
                ):
                    if not event:
                        continue
                    node_name = list(event.keys())[0]

                    yield f"data: {json.dumps({
                        'type': 'agent_start',
                        'agent': node_name
                    }, ensure_ascii=False)}\n\n"

                    yield f"data: {json.dumps({
                        'type': 'agent_complete',
                        'agent': node_name,
                        'status': 'success'
                    }, ensure_ascii=False)}\n\n"

                    await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({
                'type': 'error',
                'message': str(e)
            }, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


# ===== 数据库辅助函数 =====

async def _save_profile(db: AsyncSession, user_id: int, profile_data: dict):
    """保存或更新学生画像（6大类）"""
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    # 新画像的字段列表
    basic_fields = ["major", "grade_level", "target_role", "preferred_language"]
    json_fields = ["prior_courses", "skill_matrix", "cognitive_profile",
                   "misconception_archive", "behavior_pattern", "motivation_profile"]

    if profile:
        # 更新已有画像
        for field in basic_fields:
            if field in profile_data and profile_data[field] is not None:
                setattr(profile, field, profile_data[field])
        for field in json_fields:
            if field in profile_data and profile_data[field] is not None:
                setattr(profile, field, profile_data[field])
        if "confidence_score" in profile_data:
            profile.confidence_score = profile_data["confidence_score"]
        if "profile_version" in profile_data:
            profile.profile_version = profile_data["profile_version"]
    else:
        # 创建新画像
        profile = StudentProfile(
            user_id=user_id,
            major=profile_data.get("major"),
            grade_level=profile_data.get("grade_level"),
            target_role=profile_data.get("target_role"),
            preferred_language=profile_data.get("preferred_language"),
            prior_courses=profile_data.get("prior_courses", []),
            skill_matrix=profile_data.get("skill_matrix", {}),
            cognitive_profile=profile_data.get("cognitive_profile", {}),
            misconception_archive=profile_data.get("misconception_archive", {}),
            behavior_pattern=profile_data.get("behavior_pattern", {}),
            motivation_profile=profile_data.get("motivation_profile", {}),
            confidence_score=profile_data.get("confidence_score", 0.5),
            profile_version=profile_data.get("profile_version", 1)
        )
        db.add(profile)

    await db.commit()
    logger.info(f"[DB] 画像已保存 user_id={user_id} v{profile.profile_version}")


async def _save_resources(db: AsyncSession, user_id: int, session_id: str, output: dict):
    """保存学习资源（PostgreSQL + Milvus 双写）"""
    resource_map = {
        "document": ("document", "title"),
        "questions": ("questions", "topic"),
        "mindmap": ("mindmap", "title"),
        "code_examples": ("code_examples", "title"),
        "learning_path": ("learning_path", "title"),
        "video_result": ("video", "object_name"),
    }

    saved_resources = []

    for key, (resource_type, title_field) in resource_map.items():
        data = output.get(key)
        if not data:
            continue

        title = data.get(title_field, "") if isinstance(data, dict) else key

        resource = LearningResource(
            user_id=user_id,
            session_id=session_id,
            resource_type=resource_type,
            title=str(title)[:300],
            content=data if isinstance(data, dict) else {"data": str(data)},
            topic=output.get("user_query", "")
        )
        db.add(resource)
        saved_resources.append(resource)

    await db.commit()

    # Milvus 向量存储（异步，失败不影响主流程）
    for resource in saved_resources:
        try:
            await insert_resource({
                "resource_type": resource.resource_type,
                "title": resource.title or "",
                "topic": resource.topic or "",
                "content": resource.content,
                "user_id": user_id,
            })
        except Exception as e:
            logger.warning(f"[Milvus] 向量存储跳过 ({resource.resource_type}): {e}")

    logger.info(f"[DB] 资源已保存 user_id={user_id} count={len(saved_resources)}")


async def _save_chat_session(db: AsyncSession, user_id: int, thread_id: str,
                              history: list, message: str, assistant_reply: str = None):
    """保存对话会话（用户消息 + 助手回复）"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.thread_id == thread_id
        )
    )
    session = result.scalar_one_or_none()

    new_messages = [{"role": "user", "content": message}]
    if assistant_reply:
        new_messages.append({"role": "assistant", "content": assistant_reply})

    if session:
        existing = session.messages or []
        session.messages = existing + new_messages
        session.message_count = len(session.messages)
        session.last_message_at = datetime.utcnow()
    else:
        session = ChatSession(
            user_id=user_id,
            thread_id=thread_id,
            messages=list(history) + new_messages,
            message_count=len(history) + len(new_messages),
            last_message_at=datetime.utcnow()
        )
        db.add(session)

    await db.commit()


def _extract_assistant_summary(last_state: dict) -> str:
    """从工作流输出中提取助手回复文本（用于保存到会话上下文）"""
    parts = []
    if last_state.get("student_profile"):
        p = last_state["student_profile"]
        parts.append(f"[画像更新] {p.get('major','')} {p.get('grade_level','')}")
    if last_state.get("document"):
        parts.append(f"[学习文档] {last_state['document'].get('title','')}")
    if last_state.get("questions"):
        parts.append(f"[练习题] 共{len(last_state['questions'])}题")
    if last_state.get("mindmap"):
        parts.append("[思维导图] 已生成")
    if last_state.get("code_examples"):
        parts.append(f"[代码案例] 共{len(last_state['code_examples'])}个")
    if last_state.get("final_summary"):
        parts.append(last_state["final_summary"])
    return " | ".join(parts) if parts else "已处理"


# ===== 向量检索 API（Milvus）=====

class SearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = None
    resource_type: Optional[str] = None
    limit: int = 10


# ===== 基于现有画像触发 AI Agent 链路（无需对话） =====

@app.post("/api/profile/analyze/{user_id}")
async def analyze_profile_pipeline(user_id: int):
    """基于已有画像数据，一键触发多 Agent 协作链路，SSE 流式返回"""
    async def event_generator():
        try:
            # 1. 从数据库加载现有画像
            if not db_conn._async_session_factory:
                yield f"data: {json.dumps({'type': 'error', 'message': '数据库未初始化'}, ensure_ascii=False)}\n\n"
                return

            async with db_conn._async_session_factory() as db:
                existing_profile = await _load_existing_profile(db, user_id)
                if not existing_profile:
                    yield f"data: {json.dumps({'type': 'error', 'message': '未找到学习画像，请先完成画像构建向导'}, ensure_ascii=False)}\n\n"
                    return

                # 2. 构造分析指令（基于画像的智能分析）
                profile_summary = {
                    "major": existing_profile.get("major", "未知"),
                    "grade_level": existing_profile.get("grade_level", "未知"),
                    "target_role": existing_profile.get("target_role", "未知"),
                    "confidence_score": existing_profile.get("confidence_score", 0),
                    "skill_matrix": existing_profile.get("skill_matrix", {}),
                    "cognitive_profile": existing_profile.get("cognitive_profile", {}),
                }

                # 识别薄弱技能点
                weak_skills = []
                strong_skills = []
                skill_matrix = existing_profile.get("skill_matrix", {})
                for category, skills in skill_matrix.items():
                    if isinstance(skills, dict):
                        for skill_name, score in skills.items():
                            if isinstance(score, (int, float)):
                                if score <= 2:
                                    weak_skills.append(f"{category}/{skill_name} (得分:{score})")
                                elif score >= 4:
                                    strong_skills.append(f"{category}/{skill_name} (得分:{score})")

                synthesis = f"""基于以下学生画像进行深度分析，为该学生生成个性化机器学习学习资源：

【学生基本信息】
- 专业：{profile_summary['major']}
- 年级：{profile_summary['grade_level']}
- 目标：{profile_summary['target_role']}
- 画像置信度：{profile_summary['confidence_score']}

【薄弱环节（需重点提升）】
{'; '.join(weak_skills) if weak_skills else '暂无数据'}

【优势领域（可进一步深化）】
{'; '.join(strong_skills) if strong_skills else '暂无数据'}

请基于以上画像，生成适合该学生的：
1. 个性化教学文档
2. 针对性练习题
3. 知识思维导图
4. 代码实践案例
5. 学习路径规划"""

                logger.info(f"[ProfileAnalyze] user_id={user_id}, weak_count={len(weak_skills)}, strong_count={len(strong_skills)}")

                # 3. 执行多 Agent 工作流
                last_state = {}
                async for event in execute_workflow(
                    user_query=synthesis,
                    chat_history=[],
                    thread_id=f"profile_analyze_{user_id}_{int(datetime.utcnow().timestamp())}",
                    existing_profile=existing_profile
                ):
                    if not event:
                        continue
                    node_name = list(event.keys())[0]
                    node_output = event.get(node_name, {})
                    last_state = node_output

                    yield f"data: {json.dumps({'type': 'agent_start', 'agent': node_name}, ensure_ascii=False)}\n\n"

                    # 流式推送内容摘要
                    if isinstance(node_output, dict) and node_output:
                        if node_output.get("student_profile"):
                            yield f"data: {json.dumps({'type': 'agent_content', 'agent': node_name, 'resource_type': 'profile', 'preview': '画像分析完成'}, ensure_ascii=False)}\n\n"
                        for key in ['document', 'questions', 'mindmap', 'code_examples']:
                            val = node_output.get(key)
                            if val:
                                yield f"data: {json.dumps({'type': 'agent_content', 'agent': node_name, 'resource_type': key, 'preview': str(val)[:200]}, ensure_ascii=False)}\n\n"
                        if node_output.get("video_result"):
                            v = node_output["video_result"]
                            dur = v.get("duration", 0)
                            res = v.get("resolution", "720p")
                            vu = v.get("url", "")
                            yield "data: " + json.dumps({
                                "type": "agent_content",
                                "agent": node_name,
                                "resource_type": "video",
                                "preview": "教学视频已生成 ({}s, {})".format(dur, res),
                                "video_url": vu,
                            }, ensure_ascii=False) + "\n\n"

                    yield f"data: {json.dumps({'type': 'agent_complete', 'agent': node_name, 'status': 'success'}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)

                # 4. 持久化结果
                if last_state.get("student_profile"):
                    await _save_profile(db, user_id, last_state["student_profile"])
                    await CacheService.cache_profile(user_id, last_state["student_profile"])
                    logger.info(f"[ProfileAnalyze] 画像已更新 user_id={user_id}")

                await _save_resources(db, user_id, f"profile_analyze_{user_id}", last_state)
                summary = _extract_assistant_summary(last_state)
                await _save_chat_session(db, user_id, f"profile_analyze_{user_id}", [], synthesis, summary)

                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[ProfileAnalyze] 错误: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


# ===== 视频生成 API（独立入口）=====

class VideoGenerateRequest(BaseModel):
    topic: str
    duration: int = 5
    ratio: str = "16:9"
    resolution: str = "720p"
    mode: str = "quick"
    user_id: Optional[int] = None


@app.post("/api/video/generate")
async def api_video_generate(req: VideoGenerateRequest):
    """独立视频生成入口 —— 有画像→个性化 / 无画像→默认，SSE 流式返回"""
    async def event_generator():
        try:
            from services.llm_service import get_llm_service

            profile = None
            mode = "default"

            if req.user_id and db_conn._async_session_factory:
                async with db_conn._async_session_factory() as db:
                    profile = await _load_existing_profile(db, req.user_id)

            if req.mode == "lecture":
                yield f"data: {json.dumps({'type': 'status', 'message': '📖 完整课件模式：正在生成多章节教学脚本...', 'mode': 'lecture'}, ensure_ascii=False)}\n\n"
                video_data = await generate_lecture_script(req.topic, profile)
                yield f"data: {json.dumps({'type': 'done', 'video_url': '', 'script': video_data.get('script', ''), 'resolution': 'text', 'mode': 'lecture', 'is_fallback': True, 'is_lecture': True}, ensure_ascii=False)}\n\n"
                return

            llm = await get_llm_service()

            if profile and profile.get("confidence_score", 0) > 0.3:
                mode = "personalized"
                grade = profile.get("grade_level", "大学生")
                major = profile.get("major", "计算机")
                skill = profile.get("skill_matrix", {})
                cognitive = profile.get("cognitive_profile", {})

                weak_parts = []
                for cat, skills in skill.items():
                    if isinstance(skills, dict):
                        for name, score in skills.items():
                            if isinstance(score, (int, float)) and score <= 2.5:
                                weak_parts.append(name)
                weak_hint = ("，重点讲解: " + "、".join(weak_parts[:3])) if weak_parts else ""

                prof_conf = int(profile.get("confidence_score", 0) * 100)
                prof_label = "{} {} 画像置信度 {}%".format(major, grade, prof_conf)
                yield "data: " + json.dumps({
                    "type": "status",
                    "message": "画像模式：{}{}，正在生成个性化视频场景...".format(major, grade),
                    "mode": "personalized",
                    "profile_summary": prof_label,
                }, ensure_ascii=False) + "\n\n"

                scene_result = await llm.chat([{
                    "role": "user",
                    "content": f"为机器学习教学视频生成英文画面描述。教学主题: {req.topic}{weak_hint}。学生: {major}专业{grade}。要求: 60-150英文单词，风格: educational animation, clean modern, suitable for {major} students。只输出英文。"
                }])
            else:
                yield f"data: {json.dumps({'type': 'status', 'message': '📋 默认模式：正在生成通用视频场景...', 'mode': 'default'}, ensure_ascii=False)}\n\n"

                scene_result = await llm.chat([{
                    "role": "user",
                    "content": f"为机器学习教学视频生成英文画面描述。教学主题: {req.topic}。要求: 60-150英文单词，风格: educational animation, clean and modern。只输出英文。"
                }])

            scene_prompt = scene_result.get("content", req.topic).strip()
            if len(scene_prompt) < 10:
                scene_prompt = f"A modern educational animation explaining {req.topic}, with clean diagrams and university lecture style."

            video_data = None
            is_fallback = False

            if settings.SEEDANCE_ENABLED:
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在调用Seedance生成视频...', 'mode': mode}, ensure_ascii=False)}\n\n"
                try:
                    video_data = await generate_video(
                        prompt=scene_prompt,
                        user_id=req.user_id or 0,
                        duration=req.duration,
                        ratio=req.ratio,
                        resolution=req.resolution,
                    )
                except Exception as seedance_err:
                    logger.warning(f"[VideoGenerate] Seedance失败，降级LLM: {seedance_err}")
                    is_fallback = True

            if video_data is None:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Seedance不可用，降级为LLM生成视频脚本...', 'mode': mode}, ensure_ascii=False)}\n\n"
                video_data = await generate_video_script(req.topic)
                is_fallback = True

            title = f"教学视频 - {req.topic[:50]}"
            if req.user_id and db_conn._async_session_factory:
                try:
                    content = {
                        "url": video_data.get("url", ""),
                        "duration": video_data.get("duration", 0),
                        "ratio": video_data.get("ratio", "16:9"),
                        "resolution": video_data.get("resolution", "720p"),
                        "object_name": video_data.get("object_name", ""),
                        "stored_in_oss": video_data.get("stored_in_oss", False),
                        "scene_prompt": scene_prompt,
                        "is_fallback": is_fallback,
                    }
                    if video_data.get("script"):
                        content["script"] = video_data["script"]
                    if video_data.get("is_lecture"):
                        content["is_lecture"] = True
                    async with db_conn._async_session_factory() as db:
                        resource = LearningResource(
                            user_id=req.user_id,
                            resource_type="video",
                            title=title,
                            content=content,
                            topic=req.topic,
                        )
                        db.add(resource)
                        await db.commit()
                        logger.info(f"[VideoGenerate] 视频已保存到数据库 resource_id={resource.id}")
                except Exception as db_err:
                    logger.warning(f"[VideoGenerate] 数据库保存失败（不影响视频生成）: {db_err}")

            if is_fallback:
                yield f"data: {json.dumps({'type': 'done', 'video_url': '', 'script': video_data.get('script', ''), 'resolution': 'text', 'mode': mode, 'is_fallback': True, 'scene_prompt': scene_prompt}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'done', 'video_url': video_data.get('url', ''), 'duration': video_data.get('duration', 5), 'resolution': video_data.get('resolution', '720p'), 'ratio': video_data.get('ratio', '16:9'), 'stored_in_oss': video_data.get('stored_in_oss', False), 'scene_prompt': scene_prompt, 'mode': mode, 'is_fallback': False}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[VideoGenerate] 错误: {str(e)}", exc_info=True)
            try:
                fallback = await generate_video_script(req.topic)
                yield f"data: {json.dumps({'type': 'done', 'video_url': '', 'script': fallback.get('script', ''), 'resolution': 'text', 'mode': 'default', 'is_fallback': True}, ensure_ascii=False)}\n\n"
            except Exception as fallback_err:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.get("/api/video/providers")
async def api_video_providers():
    """返回视频 Provider 列表及配置"""
    providers = get_all_providers()
    result = []
    for pid, p in providers.items():
        result.append({
            "id": pid,
            "name": p["name"],
            "requiresApiKey": p["requiresApiKey"],
            "defaultBaseUrl": p.get("defaultBaseUrl", ""),
            "models": p.get("models", []),
            "supportedDurations": p.get("supportedDurations", [5]),
            "supportedResolutions": p.get("supportedResolutions", ["720p"]),
            "supportedAspectRatios": p.get("supportedAspectRatios", ["16:9"]),
            "enabled": pid == "seedance",
        })
    return {"success": True, "providers": result}


@app.post("/api/video/verify")
async def api_video_verify(req: dict):
    """测试视频 Provider 连通性"""
    provider_id = req.get("provider_id", "seedance")
    api_key = req.get("api_key", "")
    base_url = req.get("base_url", "")

    if not api_key:
        return {"success": False, "message": "请提供 API Key"}

    ok, msg = await test_connectivity()

    return {"success": ok, "message": msg}


@app.get("/api/video/list/{user_id}")
async def api_video_list(user_id: int, db: AsyncSession = Depends(get_db)):
    """获取用户的视频历史列表"""
    result = await db.execute(
        select(LearningResource)
        .where(
            LearningResource.user_id == user_id,
            LearningResource.resource_type == "video"
        )
        .order_by(LearningResource.created_at.desc())
        .limit(50)
    )
    videos = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": v.id,
                "title": v.title,
                "topic": v.topic,
                "content": v.content,
                "created_at": str(v.created_at) if v.created_at else None,
            }
            for v in videos
        ]
    }


@app.delete("/api/video/{resource_id}")
async def api_video_delete(resource_id: int, db: AsyncSession = Depends(get_db)):
    """删除视频记录"""
    result = await db.execute(
        select(LearningResource).where(LearningResource.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="视频记录不存在")

    if resource.resource_type != "video":
        raise HTTPException(status_code=400, detail="该资源不是视频类型")

    await db.delete(resource)
    await db.commit()

    logger.info(f"[VideoDelete] 视频记录已删除 resource_id={resource_id}")
    return {"success": True, "message": "视频记录已删除"}


@app.post("/api/search")
async def api_search(req: SearchRequest):
    """语义搜索学习资源"""
    try:
        results = await search_resources(
            query=req.query,
            user_id=req.user_id,
            resource_type=req.resource_type,
            limit=req.limit
        )
        return {"success": True, "data": results, "query": req.query}
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"success": False, "error": str(e), "data": []}


# ===== OSS API（MinIO）=====

@app.post("/api/oss/upload")
async def api_oss_upload(
    bucket: str = "uploads",
    object_name: str = "",
    user_id: int = 0
):
    """上传文件说明端点 - 实际通过 multipart 上传"""
    return {
        "message": "请使用 POST multipart/form-data 上传文件",
        "buckets": ["avatars", "mindmaps", "code_screenshots", "exports", "uploads"],
        "example": f"POST /api/oss/upload?bucket=avatars&object_name=user_{user_id}/avatar.png"
    }


@app.get("/api/oss/url")
async def api_oss_url(
    bucket: str = "mindmaps",
    object_name: str = "",
    expires_hours: int = 24
):
    """获取 MinIO 文件的临时访问链接"""
    url = await get_presigned_url(bucket, object_name, expires_hours)
    if url:
        return {"success": True, "url": url, "expires_in_hours": expires_hours}
    return {"success": False, "message": "文件不存在或MinIO未启用"}


@app.get("/api/oss/list")
async def api_oss_list(bucket: str = "mindmaps", prefix: str = ""):
    """列出 MinIO 存储桶中的文件"""
    from services.oss_service import list_files
    files = await list_files(bucket, prefix)
    return {"success": True, "bucket": bucket, "files": files}


# ===== 健康检查 =====

@app.get("/api/health")
async def health_check():
    """服务健康检查"""
    from services.vector_service import get_milvus
    from services.oss_service import get_minio

    return {
        "status": "ok",
        "services": {
            "postgresql": db_conn._async_session_factory is not None,
            "redis": db_conn._redis_client is not None,
            "milvus": get_milvus() is not None,
            "minio": get_minio() is not None,
        }
    }


if __name__ == "__main__":
    print("=" * 60)
    print(f"{settings.APP_NAME} v{settings.VERSION}")
    print(f"Frontend+Backend: http://127.0.0.1:{settings.PORT}")
    print(f"API docs: http://127.0.0.1:{settings.PORT}/docs")
    print(f"Mode: {settings.MODE}")
    print(f"DB Engine: {settings.DB_ENGINE}")
    print("=" * 60)

    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)