from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, JSON, func
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


# ===== 用户表 =====

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(120), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    resources = relationship("LearningResource", back_populates="user")
    progress = relationship("LearningProgress", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")


# ===== 学生画像表（6大类 25+维度，聚焦机器学习）=====

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # ========== 一、基础档案 (Identity) ==========
    major = Column(String(100), nullable=True, comment="专业")
    grade_level = Column(String(20), nullable=True, comment="年级（大一/大二/大三/大四/研/已工作）")
    target_role = Column(String(100), nullable=True, comment="目标职业（算法工程师/数据科学家/科研/转行）")
    prior_courses = Column(JSON, nullable=True, comment="已修课程列表 [课程名]")
    preferred_language = Column(String(30), nullable=True, comment="偏好编程语言")

    # ========== 二、技能热力图 (Skill Matrix) — ML专属细粒度评估 ==========
    skill_matrix = Column(JSON, nullable=True, comment="""
    {
      "math": {
        "linear_algebra": 1-5, "probability": 1-5,
        "calculus": 1-5, "statistics": 1-5, "optimization": 1-5
      },
      "programming": {
        "python": 1-5, "numpy": 1-5, "pandas": 1-5,
        "data_structure": 1-5, "algorithm": 1-5, "sql": 1-5
      },
      "machine_learning": {
        "supervised": 1-5, "unsupervised": 1-5,
        "neural_networks": 1-5, "deep_learning": 1-5,
        "nlp": 1-5, "cv": 1-5, "reinforcement": 1-5,
        "feature_engineering": 1-5, "model_evaluation": 1-5,
        "mlops": 1-5, "ensemble_methods": 1-5
      },
      "tools": {
        "sklearn": 1-5, "pytorch": 1-5, "tensorflow": 1-5,
        "jupyter": 1-5, "git": 1-5, "docker": 1-5,
        "matplotlib": 1-5, "mlflow": 1-5
      }
    }""")

    # ========== 三、认知画像 (Cognitive Profile) — 决定怎么教 ==========
    cognitive_profile = Column(JSON, nullable=True, comment="""
    {
      "bloom_level": "remember/understand/apply/analyze/evaluate/create",
      "learning_style": "visual/auditory/reading/kinesthetic",
      "abstraction_ability": 1-5,
      "mathematical_maturity": 1-5,
      "question_depth": "surface/medium/deep",
      "learning_pace": "slow/medium/fast",
      "prefers_theory_first": true/false,
      "needs_concrete_examples": true/false,
      "attention_to_detail": 1-5
    }""")

    # ========== 四、易错档案 (Misconception Archive) — 决定练什么 ==========
    misconception_archive = Column(JSON, nullable=True, comment="""
    {
      "concept_misunderstandings": [
        {"concept": "过拟合", "error": "认为模型越复杂越好", "frequency": 3}
      ],
      "math_blind_spots": ["矩阵求导", "贝叶斯公式"],
      "coding_bad_habits": ["不划分验证集", "特征未归一化"],
      "high_error_topics": ["梯度消失", "正则化"],
      "exam_mistake_types": [
        {"type": "推导题", "error_rate": 0.6},
        {"type": "调参实践", "error_rate": 0.3}
      ]
    }""")

    # ========== 五、学习行为 (Behavior Pattern) — 决定怎么推 ==========
    behavior_pattern = Column(JSON, nullable=True, comment="""
    {
      "completion_rate": 0.0-1.0,
      "avg_session_minutes": 数字,
      "active_time_of_day": "morning/afternoon/evening/night",
      "content_format_preference": ["document","video","code","interactive"],
      "exercise_type_preference": "multiple_choice/coding/project/open_ended",
      "hint_usage_rate": 0.0-1.0,
      "review_frequency": 0.0-1.0,
      "drop_off_topics": ["变分推断"],
      "persistence_score": 1-5
    }""")

    # ========== 六、动机画像 (Motivation Engine) — 决定推什么方向 ==========
    motivation_profile = Column(JSON, nullable=True, comment="""
    {
      "primary_motivation": "job_hunting/research/career_change/curiosity/exam",
      "urgency_level": 1-5,
      "self_efficacy": 1-5,
      "topic_passion": [
        {"topic": "GAN", "interest": 0.9},
        {"topic": "推荐系统", "interest": 0.7}
      ],
      "career_target": "算法工程师",
      "burnout_risk": "low/medium/high",
      "preferred_reward": "achievement/progress/social"
    }""")

    # ========== 七、能力矩阵（来自向导评估）==========
    # 格式: {chapter: {kp: {score, confidence, notes}}}
    # 7章 28个知识点，覆盖完整机器学习知识图谱
    capability_matrix = Column(JSON, nullable=True, comment="向导评估能力矩阵")

    overall_score = Column(Float, nullable=True, comment="综合得分 (百分制)")

    # ========== 八、向导评估结果（完整记录）==========
    profile_detail = Column(JSON, nullable=True, comment="""
    完整画像详情：
    {
      "basic_info": {major, degree, grade, school, preferred_language},
      "learning_goals": {target_role, deadline, motivation, weekly_hours},
      "prior_experience": {courses_taken, projects, self_assessment},
      "uploaded_document": {format, char_count, extracted_info},
      "quiz_result": {total_questions, correct_count, completion_rate},
      "advanced_interest": {nlp, cv, reinforcement_learning, mlops}
    }""")

    # ========== 元数据 ==========
    confidence_score = Column(Float, nullable=True, comment="画像整体置信度 (0-1)")
    profile_version = Column(Integer, default=1, comment="画像版本号（每次更新+1）")
    last_updated_from = Column(String(50), nullable=True, comment="最近一次更新来源（对话ID）")

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


# ===== 学习资源表 =====

class LearningResource(Base):
    __tablename__ = "learning_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, comment="会话ID")

    # 资源类型: document/questions/mindmap/code_examples/learning_path
    resource_type = Column(String(30), nullable=False)

    # 内容
    title = Column(String(300), nullable=True)
    content = Column(JSON, nullable=True, comment="资源内容（JSON格式）")
    raw_text = Column(Text, nullable=True, comment="原始文本")

    # 元数据
    topic = Column(String(200), nullable=True, comment="学习主题")
    difficulty = Column(String(20), nullable=True, comment="初级/中级/高级")
    tokens_used = Column(Integer, default=0, comment="生成消耗的tokens")

    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="resources")


# ===== 学习进度表 =====

class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 进度信息
    stage_name = Column(String(100), nullable=False, comment="阶段名称")
    stage_index = Column(Integer, nullable=False, comment="阶段序号")
    progress_pct = Column(Float, default=0.0, comment="完成百分比")
    status = Column(String(20), default="pending", comment="pending/in_progress/completed")

    # 关联数据
    completed_exercises = Column(Integer, default=0)
    total_exercises = Column(Integer, default=0)
    time_spent_minutes = Column(Float, default=0.0)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="progress")


# ===== 对话会话表 =====

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, index=True, comment="LangGraph线程ID")

    # 对话内容
    messages = Column(JSON, nullable=True, comment="完整对话记录 [{role, content}]")
    message_count = Column(Integer, default=0)

    # 会话状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_message_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="chat_sessions")


class LearningMaterial(Base):
    __tablename__ = "learning_materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chapter_id = Column(String(50), nullable=False, index=True)
    stage = Column(String(20), nullable=False, comment="seedling/sprout/practice/advanced/master")
    mastery_at_creation = Column(Float, default=0.0)
    content = Column(JSON, nullable=True, comment="{document: {title, content, sections}, questions: [...], doc_sections: [{id, title, content}]}")
    profile_snapshot = Column(JSON, nullable=True)
    weak_points = Column(JSON, nullable=True, comment="[knowledge_point, ...]")
    is_current = Column(Boolean, default=True)
    review_count = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class MasteryHistory(Base):
    __tablename__ = "mastery_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chapter_id = Column(String(50), nullable=False, index=True)
    mastery = Column(Float, nullable=False)
    source = Column(String(30), nullable=False, comment="quiz/doc/review/initial/generation")
    detail = Column(JSON, nullable=True, comment="{old_mastery, new_mastery, delta, question_id, ...}")
    created_at = Column(DateTime, server_default=func.now())

class WeakPoint(Base):
    __tablename__ = "weak_points"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chapter_id = Column(String(50), nullable=False, index=True)
    knowledge_point = Column(String(200), nullable=False)
    doc_section_id = Column(String(50), nullable=True)
    status = Column(String(20), default="active", comment="active/resolved")
    occurrence_count = Column(Integer, default=1)
    first_seen_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_type = Column(String(30), nullable=False, comment="exam/project/paper/intro/remedial/extend/custom")
    goal_detail = Column(String(300), nullable=True, comment="目标描述，如'2周内掌握Transformer'")
    deadline = Column(DateTime, nullable=True)
    weekly_hours = Column(Float, default=10.0)
    chapter_ids = Column(JSON, nullable=False, comment="[chapter_id, ...]")
    schedule = Column(JSON, nullable=True, comment="[{date, chapter_id, task_type, duration_min, status}]")
    status = Column(String(20), default="active", comment="active/completed/abandoned")
    profile_snapshot = Column(JSON, nullable=True)
    progress_pct = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlanTask(Base):
    __tablename__ = "plan_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chapter_id = Column(String(50), nullable=False, index=True)
    task_type = Column(String(30), nullable=False, comment="new_learn/review/quiz/derivation/code_lab/exam/compare/report")
    task_date = Column(DateTime, nullable=True)
    duration_min = Column(Integer, default=60)
    status = Column(String(20), default="pending", comment="pending/in_progress/completed/skipped")
    result = Column(JSON, nullable=True, comment="{score, correct_rate, time_spent, ...}")
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)


class ExamPaper(Base):
    __tablename__ = "exam_papers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam_type = Column(String(30), nullable=False, comment="mock/derivation/compare/code_lab/report")
    chapter_ids = Column(JSON, nullable=False)
    questions = Column(JSON, nullable=False, comment="[{type, content, answer, options, steps, ...}]")
    answers = Column(JSON, nullable=True, comment="用户提交的答案")
    score = Column(Float, nullable=True)
    total_score = Column(Float, default=100.0)
    time_limit_min = Column(Integer, default=120)
    time_spent_sec = Column(Integer, default=0)
    status = Column(String(20), default="draft", comment="draft/in_progress/completed")
    profile_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)