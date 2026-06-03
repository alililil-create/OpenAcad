from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import AgentState
from agents.profile_agent import ProfileAgent
from agents.document_agent import DocumentAgent
from agents.question_agent import QuestionAgent
from agents.mindmap_agent import MindmapAgent
from agents.code_agent import CodeAgent
from agents.path_agent import PathAgent
from agents.tutor_agent import TutorAgent
import logging

logger = logging.getLogger(__name__)


def create_learning_graph():
    """
    创建多智能体学习资源生成工作流

    三种模式：
    1. FULL_PIPELINE: 完整流程（新知识学习）
    2. PRACTICE_MODE: 练习模式（只生成题目）
    3. TUTOR_MODE: 辅导模式（智能答疑）
    """

    workflow = StateGraph(AgentState)

    # 初始化所有Agent
    profile_agent = ProfileAgent()
    doc_agent = DocumentAgent()
    question_agent = QuestionAgent()
    mindmap_agent = MindmapAgent()
    code_agent = CodeAgent()
    path_agent = PathAgent()
    tutor_agent = TutorAgent()

    # ===== 添加节点 =====
    workflow.add_node("analyze_intent", intent_router_node)
    workflow.add_node("build_profile", profile_agent)
    workflow.add_node("generate_doc", doc_agent)
    workflow.add_node("generate_questions", question_agent)
    workflow.add_node("generate_mindmap", mindmap_agent)
    workflow.add_node("generate_code", code_agent)
    workflow.add_node("plan_path", path_agent)
    workflow.add_node("tutor_answer", tutor_agent)
    workflow.add_node("final_summary", summary_generator_node)

    # ===== 设置入口 =====
    workflow.set_entry_point("analyze_intent")

    # ===== 条件路由函数 =====
    def route_by_intent(state: AgentState) -> str:
        """根据用户意图决定走哪个分支"""
        intent = state.get("user_intent", "learn")

        logger.info(f"[Router] 用户意图: {intent}")

        if intent == "learn":
            return "build_profile"
        elif intent == "practice":
            return "build_profile"
        elif intent == "ask_tutor":
            return "build_profile"
        elif intent == "view_path":
            return "plan_path"
        else:
            return "build_profile"

    # ===== 添加条件边 =====
    workflow.add_conditional_edges(
        "analyze_intent",
        route_by_intent,
        {
            "build_profile": "build_profile",
            "plan_path": "plan_path"
        }
    )

    # ===== 主流程边（线性流水线 - 最稳定）=====
    workflow.add_edge("build_profile", "generate_doc")
    workflow.add_edge("generate_doc", "generate_questions")
    workflow.add_edge("generate_questions", "generate_mindmap")
    workflow.add_edge("generate_mindmap", "generate_code")
    workflow.add_edge("generate_code", "plan_path")
    workflow.add_edge("plan_path", "final_summary")
    workflow.add_edge("final_summary", END)

    # ===== 编译图 =====
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    logger.info("[Workflow] 图编译完成")
    return app


# ===== 辅助节点函数 =====

async def intent_router_node(state: AgentState) -> dict:
    """意图识别节点 - 使用LLM判断用户想做什么"""
    from services.llm_service import get_llm_service

    llm = await get_llm_service()

    # 获取最近10条历史消息作为上下文
    messages = state.get('messages', [])
    recent_context = messages[-10:] if messages else []
    context_str = "\n".join(
        [f"{m['role']}: {str(m.get('content', ''))[:200]}" for m in recent_context]
    ) if recent_context else "无历史对话"

    prompt = f"""分析用户的意图，返回以下之一：
- learn: 想学习新知识/新概念
- practice: 想做练习题/测试
- ask_tutor: 有具体问题需要解答
- view_path: 想查看/修改学习计划

对话历史上下文：
{context_str}

用户最新输入：{state.get('user_query', '')}

只返回意图关键词，不要解释。"""

    result = await llm.chat(
        [{"role": "user", "content": prompt}],
        cache_agent="intent",
        cache_chapter="intent_router",
        cache_stage="na",
        cache_profile_hash="",
        cache_user_id=int(state.get("user_id") or 0),
        use_cache=False,
        write_cache=False,
    )
    intent = result["content"].strip().lower()

    valid_intents = ["learn", "practice", "ask_tutor", "view_path"]
    if intent not in valid_intents:
        intent = "learn"

    return {"user_intent": intent}


async def summary_generator_node(state: AgentState) -> dict:
    """最终总结节点 - 整合所有Agent的产出"""

    summary_parts = []

    if state.get("document"):
        summary_parts.append(f"📄 已生成讲解文档《{state['document']['title']}》")

    if state.get("questions"):
        summary_parts.append(f"✏️ 已生成{len(state['questions'])}道练习题")

    if state.get("mindmap"):
        summary_parts.append("🗺️ 已生成思维导图")

    if state.get("code_examples"):
        summary_parts.append(f"💻 已生成{len(state['code_examples'])}个代码案例")

    if state.get("learning_path"):
        summary_parts.append(f"🛤️ 已制定{len(state['learning_path'])}步学习路径")

    if state.get("tutor_response"):
        summary_parts.append("🎓 智能辅导回复已准备")

    final_text = "\n".join(summary_parts) if summary_parts else "✅ 处理完成"

    return {
        "final_summary": final_text,
        "current_agent": "summary"
    }


# ===== 工作流执行器 =====

async def execute_workflow(
    user_query: str,
    chat_history: list = [],
    thread_id: str = "default",
    existing_profile: dict = None,
    user_id: int = 0
):
    """
    执行多Agent工作流（主入口）

    Args:
        user_query: 用户输入
        chat_history: 对话历史 [{"role": "user/content", ...}]
        thread_id: 会话ID（用于状态恢复）
        existing_profile: 已有的学生画像（用于多轮对话中优化而非重建）
        user_id: 用户ID（透传到所有 Agent，保证 LLM 缓存按用户隔离）

    Returns:
        最终状态字典
    """
    graph = create_learning_graph()

    initial_state: AgentState = {
        "messages": chat_history,
        "user_query": user_query,
        "user_id": user_id,
        "user_intent": "",
        "student_profile": existing_profile,  # 注入已有画像 → 优化而非重建
        "profile_confidence": 0.0,
        "document": None,
        "mindmap": None,
        "questions": None,
        "code_examples": None,
        "reading_materials": None,
        "learning_path": None,
        "tutor_response": None,
        "final_summary": None,
        "current_agent": "",
        "execution_log": [],
        "errors": [],
        "processing_time": {},
        "total_tokens_used": 0
    }

    config = {"configurable": {"thread_id": thread_id}}

    final_state = None
    async for event in graph.astream(initial_state, config=config):
        node_name = list(event.keys())[0]
        logger.info(f"[Workflow] 节点 '{node_name}' 完成")
        yield event
        final_state = event
