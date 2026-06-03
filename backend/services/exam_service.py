import json
import logging
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ExamPaper, StudentProfile, MasteryHistory
from services.knowledge_graph import KNOWLEDGE_GRAPH, CHAPTER_ORDER
from services.material_service import get_stage, STAGE_CONFIG, get_user_chapter_mastery

logger = logging.getLogger(__name__)

EXAM_TYPE_CONFIG = {
    "mock": {"label": "🧪 期末模拟", "time_min": 120, "question_types": ["choice", "fill", "derivation", "calculation", "essay"]},
    "derivation": {"label": "📐 推导专练", "time_min": 60, "question_types": ["derivation"]},
    "compare": {"label": "⚖️ 算法对比", "time_min": 45, "question_types": ["compare"]},
    "code_lab": {"label": "💻 代码实验", "time_min": 90, "question_types": ["code"]},
    "report": {"label": "📊 实验报告", "time_min": 120, "question_types": ["report"]},
}

QUESTION_TYPE_WEIGHTS = {
    "mock": {"choice": 30, "fill": 20, "derivation": 15, "calculation": 20, "essay": 15},
    "derivation": {"derivation": 100},
    "compare": {"compare": 100},
    "code_lab": {"code": 100},
    "report": {"report": 100},
}

def _build_exam_prompt(exam_type: str, chapter_ids: list, chapter_scores: dict, profile: dict = None, user_id: int = 0) -> str:
    chapters_info = []
    for ch_id in chapter_ids:
        ch = KNOWLEDGE_GRAPH.get(ch_id, {})
        score = chapter_scores.get(ch_id, 0)
        mastery = score / 100 * 5
        stage = get_stage(mastery)
        stage_cfg = STAGE_CONFIG.get(stage, STAGE_CONFIG["seedling"])
        kps = [kp["name"] for kp in ch.get("knowledge_points", [])]
        chapters_info.append(f"- {ch.get('icon','')} {ch.get('name',ch_id)}: 掌握度{mastery:.1f}/5.0, 阶段{stage_cfg['label']}, 知识点: {', '.join(kps)}")

    chapters_text = "\n".join(chapters_info)
    type_cfg = EXAM_TYPE_CONFIG.get(exam_type, EXAM_TYPE_CONFIG["mock"])
    weights = QUESTION_TYPE_WEIGHTS.get(exam_type, QUESTION_TYPE_WEIGHTS["mock"])
    profile_text = ""
    if profile:
        weak = []
        cap = profile.get("capability_matrix") or {}
        if isinstance(cap, dict):
            for ch_id, ch_data in cap.items():
                if isinstance(ch_data, dict):
                    kp_map = ch_data.get("知识点掌握度", ch_data)
                    if isinstance(kp_map, dict):
                        for kp, v in kp_map.items():
                            if isinstance(v, dict) and v.get("score", 0) <= 2:
                                weak.append(f"{ch_id}/{kp}")
        profile_text = (
            f"\n学生画像: 专业={profile.get('major','未知')}, "
            f"年级={profile.get('grade_level','未知')}, "
            f"目标={profile.get('target_role','未知')}, "
            f"偏好语言={profile.get('preferred_language','Python')}"
        )
        if weak:
            profile_text += f"\n薄弱知识点（重点出题）: {', '.join(weak[:10])}"
    if user_id:
        profile_text += f"\n[exam_user_id={user_id} | exam_type={exam_type} | chapter_ids={','.join(chapter_ids)}]"

    if exam_type == "derivation":
        return f"""你是机器学习课程推导教练。为以下章节生成逐步推导题，每道题包含多个步骤，每步有提示和答案。

章节信息：
{chapters_text}
{profile_text}

要求：
1. 生成3道推导题，覆盖核心知识点
2. 每道题格式：
{{
  "type": "derivation",
  "title": "推导题标题",
  "content": "题目描述",
  "steps": [
    {{"step": 1, "instruction": "写出假设函数", "hint": "回顾线性模型的形式", "answer": "h(x)=w^Tx+b", "points": 5}},
    {{"step": 2, "instruction": "写出损失函数", "hint": "使用均方误差", "answer": "J(w)=1/2m Σ(h(x_i)-y_i)^2", "points": 5}},
    ...
  ],
  "total_points": 15,
  "difficulty": 3,
  "chapter_id": "章节ID",
  "knowledge_point": "知识点名"
}}

请严格返回JSON数组，不要其他文字。"""

    elif exam_type == "compare":
        return f"""你是机器学习课程算法对比专家。为以下章节生成算法对比分析题。

章节信息：
{chapters_text}
{profile_text}

要求：
1. 生成2组算法对比，每组对比2-3个算法
2. 每组格式：
{{
  "type": "compare",
  "title": "算法对比标题",
  "algorithms": ["算法A", "算法B"],
  "dimensions": [
    {{"name": "目标函数", "values": ["算法A的目标", "算法B的目标"]}},
    {{"name": "适用场景", "values": ["算法A的场景", "算法B的场景"]}},
    {{"name": "优缺点", "values": ["算法A的优缺点", "算法B的优缺点"]}}
  ],
  "questions": [
    {{"content": "以下场景适合用哪个算法？", "options": ["算法A", "算法B", "两者皆可", "两者都不"], "answer": 0, "explanation": "原因..."}}
  ],
  "chapter_ids": ["章节ID1", "章节ID2"],
  "difficulty": 3
}}

请严格返回JSON数组。"""

    elif exam_type == "code_lab":
        return f"""你是机器学习课程代码实验教练。为以下章节生成代码实验题。

章节信息：
{chapters_text}
{profile_text}

要求：
1. 生成2道代码实验题
2. 每道题格式：
{{
  "type": "code",
  "title": "代码实验标题",
  "description": "实验描述和目标",
  "skeleton": "Python代码骨架，关键部分用TODO标记",
  "hints": ["提示1", "提示2"],
  "test_cases": [
    {{"input": "测试输入描述", "expected_output": "期望输出描述"}}
  ],
  "reference_solution": "完整参考实现",
  "chapter_id": "章节ID",
  "difficulty": 3,
  "estimated_min": 30
}}

请严格返回JSON数组。"""

    elif exam_type == "report":
        return f"""你是机器学习课程实验报告助手。为以下章节生成实验报告框架。

章节信息：
{chapters_text}
{profile_text}

要求：
1. 生成1份实验报告框架
2. 格式：
{{
  "type": "report",
  "title": "实验报告标题",
  "sections": [
    {{"heading": "一、实验目的", "content": "实验目的描述", "template": "掌握...的原理和实现"}},
    {{"heading": "二、实验环境", "content": "", "template": "Python 3.10, scikit-learn, numpy, matplotlib"}},
    {{"heading": "三、实验步骤", "content": "", "subsections": [
      {{"title": "3.1 数据准备", "template": "# 加载数据\\nfrom sklearn.datasets import ..."}},
      {{"title": "3.2 模型训练", "template": "# 训练模型\\nfrom sklearn.xxx import ..."}},
      {{"title": "3.3 结果分析", "template": "# 可视化和评估"}}
    ]}},
    {{"heading": "四、实验结果", "content": "", "template": "插入实验截图和表格"}},
    {{"heading": "五、分析与讨论", "content": "", "questions": ["为什么...", "如果改变...会怎样？"]}}
  ],
  "chapter_ids": ["章节ID"],
  "difficulty": 3
}}

请严格返回JSON。"""

    else:
        return f"""你是机器学习课程考试出题专家。为以下章节生成期末模拟试卷。

章节信息：
{chapters_text}
{profile_text}

题型分值权重：{json.dumps(weights, ensure_ascii=False)}

要求：
1. 按分值权重生成题目，总分100分
2. 题目格式：
- 选择题: {{"type": "choice", "content": "题干", "options": ["A选项","B选项","C选项","D选项"], "answer": 0, "points": 3, "chapter_id": "...", "difficulty": 2}}
- 填空题: {{"type": "fill", "content": "题干___空___", "answer": "答案", "points": 2, "chapter_id": "...", "difficulty": 2}}
- 推导题: {{"type": "derivation", "content": "推导...", "steps": [{{"step":1,"instruction":"...","answer":"..."}}], "points": 15, "chapter_id": "...", "difficulty": 4}}
- 计算题: {{"type": "calculation", "content": "计算...", "data": "给定数据...", "answer": "最终答案", "steps": ["步骤1","步骤2"], "points": 20, "chapter_id": "...", "difficulty": 3}}
- 简答题: {{"type": "essay", "content": "简述...", "key_points": ["要点1","要点2"], "points": 15, "chapter_id": "...", "difficulty": 3}}

3. 薄弱章节({{score<60}})多出题，已掌握章节少出题
4. 难度分布：基础40%, 中等40%, 困难20%

请严格返回JSON数组。"""


def _parse_questions(raw: str) -> list:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return [json.loads(text[start:end+1])]
            except:
                pass
    return []


async def create_exam(db: AsyncSession, user_id: int, exam_type: str, chapter_ids: list) -> ExamPaper:
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    chapter_scores = {}
    if profile and profile.capability_matrix:
        for ch_id, kp_data in profile.capability_matrix.items():
            if isinstance(kp_data, dict):
                scores = [v.get("score", 0) for v in kp_data.values() if isinstance(v, dict) and "score" in v]
                if scores:
                    chapter_scores[ch_id] = sum(scores) / len(scores)
    profile_dict = None
    if profile:
        profile_dict = {
            "major": profile.major,
            "grade_level": profile.grade_level,
            "target_role": profile.target_role,
            "preferred_language": profile.preferred_language,
            "capability_matrix": profile.capability_matrix,
        }
    type_cfg = EXAM_TYPE_CONFIG.get(exam_type, EXAM_TYPE_CONFIG["mock"])
    prompt = _build_exam_prompt(exam_type, chapter_ids, chapter_scores, profile_dict, user_id=user_id)
    from services.llm_service import get_llm_service
    llm = await get_llm_service()
    chat_result = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        cache_agent="exam",
        cache_chapter="|".join(chapter_ids)[:64] if chapter_ids else "all",
        cache_stage=exam_type,
        cache_profile_hash=f"u{user_id}",
        cache_user_id=user_id,
        use_cache=False,
        write_cache=False,
    )
    raw_response = chat_result.get("content", "")
    questions = _parse_questions(raw_response)
    exam = ExamPaper(
        user_id=user_id, exam_type=exam_type, chapter_ids=chapter_ids,
        questions=questions, status="draft", profile_snapshot=profile_dict,
        time_limit_min=type_cfg["time_min"],
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)
    return exam


async def get_exam(db: AsyncSession, exam_id: int) -> ExamPaper:
    result = await db.execute(select(ExamPaper).where(ExamPaper.id == exam_id))
    return result.scalar_one_or_none()


async def submit_exam(db: AsyncSession, exam_id: int, answers: list, time_spent_sec: int = 0) -> dict:
    result = await db.execute(select(ExamPaper).where(ExamPaper.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        return {"error": "试卷不存在"}
    exam.answers = answers
    exam.time_spent_sec = time_spent_sec
    exam.status = "completed"
    exam.completed_at = datetime.utcnow()
    score = 0
    total = 0
    grading = []
    for i, q in enumerate(exam.questions):
        pts = q.get("points", 0)
        total += pts
        ans = answers[i] if i < len(answers) else None
        correct = False
        if q.get("type") == "choice":
            correct = ans == q.get("answer")
        elif q.get("type") == "fill":
            correct = ans and ans.strip().lower() == str(q.get("answer", "")).strip().lower()
        else:
            correct = ans is not None and len(str(ans)) > 5
        earned = pts if correct else pts * 0.3 if ans else 0
        score += earned
        grading.append({"question_index": i, "correct": correct, "earned": round(earned, 1), "total": pts})
    exam.score = round(score, 1)
    exam.total_score = total
    await db.commit()
    return {"exam_id": exam_id, "score": exam.score, "total_score": total, "grading": grading}


async def get_user_exams(db: AsyncSession, user_id: int, exam_type: str = None) -> list:
    conditions = [ExamPaper.user_id == user_id]
    if exam_type:
        conditions.append(ExamPaper.exam_type == exam_type)
    result = await db.execute(
        select(ExamPaper).where(and_(*conditions)).order_by(desc(ExamPaper.created_at)).limit(20)
    )
    return result.scalars().all()
