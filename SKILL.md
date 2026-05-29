---
name: "ml-agent-upgrader"
description: "将纯前端ML学习平台升级为LangGraph多智能体全栈系统。当用户有HTML/CSS/JS前端项目需要接入AI大模型、多Agent协作、后端服务时调用此技能。"
---

# ML学习平台 - LangGraph多智能体系统升级技能

## 📌 技能概述

本技能用于将**纯前端的机器学习个性化学习平台**升级为**基于LangGraph的多智能体协作全栈系统**。

### 适用场景

- ✅ 现有项目是纯HTML/CSS/JavaScript前端（无后端）
- ✅ 需要接入真实的大模型能力（如讯飞星火）
- ✅ 需要实现多智能体（Multi-Agent）协作机制
- ✅ 需要满足"中国软件杯"A3赛题要求
- ✅ 当前使用localStorage存储，需改为数据库持久化

---

## 🎯 升级目标对照表

| 赛题要求 | 升级前状态 | 升级后目标 |
|---------|-----------|-----------|
| **多智能体架构** | ❌ 无 | ✅ 7个专业Agent + LangGraph编排 |
| **大模型接入** | ❌ 预设逻辑 | ✅ 讯飞星火真实调用 |
| **多模态资源生成** | ⚠️ 2种类型 | ✅ ≥5种类型 |
| **学生画像(≥6维)** | ⚠️ 8维静态 | ✅ 动态构建+随学随新 |
| **流式输出** | ❌ 无 | ✅ SSE实时推送 |
| **数据安全** | ❌ localStorage | ✅ SQLite数据库 |
| **后端服务** | ❌ 无 | ✅ FastAPI完整服务 |

---

## 📦 第一步：创建后端项目结构

在项目根目录执行以下操作：

### 1.1 创建目录结构

```
你的项目根目录/
├── backend/                          # 新增：后端代码
│   ├── app.py                        # FastAPI入口文件
│   ├── config.py                     # 配置管理
│   ├── requirements.txt              # Python依赖
│   │
│   ├── graph/                        # LangGraph工作流
│   │   ├── __init__.py
│   │   ├── state.py                  # 【核心】共享状态定义
│   │   └── workflow.py               # 【核心】工作流编排
│   │
│   ├── agents/                       # 7个专业Agent
│   │   ├── __init__.py
│   │   ├── profile_agent.py          # Agent 1: 画像构建
│   │   ├── document_agent.py         # Agent 2: 文档生成
│   │   ├── question_agent.py         # Agent 3: 题库生成
│   │   ├── mindmap_agent.py          # Agent 4: 思维导图
│   │   ├── code_agent.py             # Agent 5: 代码案例
│   │   ├── path_agent.py             # Agent 6: 路径规划
│   │   └── tutor_agent.py            # Agent 7: 智能辅导(可选)
│   │
│   ├── services/                     # 服务层
│   │   ├── __init__.py
│   │   ├── llm_service.py            # 大模型封装
│   │   ├── db_service.py             # 数据库操作
│   │   └── storage_service.py        # 文件存储
│   │
│   ├── models/                       # 数据模型
│   │   ├── __init__.py
│   │   ├── schemas.py                # Pydantic模型
│   │   └── database.py               # SQLAlchemy模型
│   │
│   └── utils/                        # 工具函数
│       ├── __init__.py
│       ├── helpers.py                # 辅助函数
│       └── prompts.py                # Prompt模板库
│
├── frontend/                         # 改造后的前端（原文件移入或保留在根目录）
│   ├── (原有HTML/CSS/JS文件)
│   └── scripts/
│       └── api.js                    # 新增：API对接层
│
├── .env                              # 新增：环境变量配置
├── docker-compose.yml                # 新增：Docker部署配置
└── README.md                         # 更新：项目说明
```

### 1.2 创建 `backend/requirements.txt`

```txt
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# LangGraph & LangChain
langgraph==0.0.55
langchain==0.1.0
langchain-openai==0.0.2

# 数据库
sqlalchemy==2.0.23
aiosqlite==0.19.0

# HTTP客户端
httpx==0.25.2

# 认证与加密
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# 配置管理
python-dotenv==1.0.0
pydantic==2.5.2
pydantic-settings==2.1.0

# 异步支持
aiofiles==23.2.1
```

---

## 🔧 第二步：创建核心文件（按顺序）

### 文件1：`backend/config.py` - 配置管理

```python
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置 - 从环境变量读取"""
    
    # 应用基础配置
    APP_NAME: str = "ML Learning Agent System"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 讯飞星火配置【必须填写】
    XUNFEI_API_KEY: str = ""           # 从 https://www.xfyun.cn/ 获取
    XUNFEI_APP_ID: str = ""
    XUNFEI_API_SECRET: str = ""
    
    # 模型选择
    LLM_MODEL: str = "X2"              # X2 / 4.0-turbo / X1.5(推理)
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./ml_learning.db"
    
    # JWT认证配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # CORS配置（允许前端跨域访问）
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:5500", "*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    """获取设置单例"""
    return settings
```

### 文件2：`backend/graph/state.py` - LangGraph状态定义（最关键）

这是整个系统的**核心数据结构**，所有Agent之间通过这个状态传递数据：

```python
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages


class StudentProfile(TypedDict):
    """学生画像 - 必须包含≥6个维度"""
    major: str                    # 专业背景
    grade_level: str              # 年级水平
    math_foundation: int          # 数学基础 1-5分
    programming_exp: int          # 编程经验 1-5分
    ml_knowledge: int             # ML知识储备 1-5分
    learning_style: str           # 学习风格
    learning_goal: str            # 学习目标
    weak_points: List[str]        # 薄弱环节
    weekly_hours: int             # 每周学习时间
    interests: List[str]          # 兴趣方向
    preferred_language: str       # 偏好编程语言


class GeneratedDocument(TypedDict):
    """生成的文档资源"""
    content: str                  # Markdown内容
    title: str                    # 标题
    topic: str                    # 知识点
    difficulty: str               # 难度等级
    estimated_time: int           # 预计阅读时间(分钟)
    tags: List[str]               # 标签


class QuestionItem(TypedDict):
    """练习题目"""
    id: str
    type: str                     # choice/fill_blank/coding/case_study
    question: str
    options: Optional[List[str]]
    answer: str
    explanation: str
    difficulty: int               # 1-5
    knowledge_point: str
    hints: List[str]


class CodeExample(TypedDict):
    """代码实操案例"""
    title: str
    language: str
    code: str
    explanation: str
    comments: List[str]           # 逐行注释
    expected_output: str
    prerequisites: List[str]
    complexity: str


class LearningPathStep(TypedDict):
    """学习路径步骤"""
    step_number: int
    topic: str
    description: str
    resources: List[Dict]
    estimated_hours: int
    prerequisites: List[str]
    status: str                   # not_started/in_progress/completed


class AgentState(TypedDict):
    """
    【核心】LangGraph共享状态
    
    设计原则：
    1. 每个Agent只读取自己需要的字段
    2. 每个Agent只返回自己生成的字段
    3. LangGraph自动合并返回的状态
    """
    
    # === 用户输入层 ===
    messages: List[dict]
    user_query: str
    user_intent: str              # learn/practice/ask_plan/tutor
    
    # === 学生画像层 ===
    student_profile: Optional[StudentProfile]
    profile_confidence: float     # 0-1
    
    # === 资源生成层 ===
    document: Optional[GeneratedDocument]
    mindmap: Optional[str]        # Markdown格式思维导图
    questions: Optional[List[QuestionItem]]
    code_examples: Optional[List[CodeExample]]
    reading_materials: Optional[List[Dict]]
    
    # === 规划与输出层 ===
    learning_path: Optional[List[LearningPathStep]]
    tutor_response: Optional[str]
    final_summary: Optional[str]
    
    # === 控制与元数据 ===
    current_agent: str            # 当前执行的Agent名称
    execution_log: List[Dict]     # 执行日志（用于可视化）
    errors: List[str]
    processing_time: Dict[str, float]
    total_tokens_used: int
```

### 文件3：`backend/services/llm_service.py` - 讯飞星火封装

```python
import httpx
import json
import time
from typing import AsyncGenerator, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """大模型配置"""
    api_key: str
    app_id: str
    api_secret: str
    model: str = "X2"
    base_url: str = "https://spark-api.xf-yun.com/v3.5/chat"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0


class XingHuoLLMService:
    """
    讯飞星火大模型服务
    
    功能：
    1. 同步/异步对话
    2. 流式输出（SSE）- 用于打字机效果
    3. 结构化输出 - 强制JSON格式
    4. Token计数和错误重试
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout, connect=10.0)
        )
        self.total_tokens_used = 0
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """非流式对话"""
        
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages
        
        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": False,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-App-Id": self.config.app_id
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(
                self.config.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "processing_time": time.time() - start_time,
                "model": self.config.model
            }
            
        except httpx.HTTPStatusError as e:
            raise Exception(f"API请求失败 [{e.response.status_code}]: {e.response.text}")
        except Exception as e:
            raise Exception(f"调用大模型失败: {str(e)}")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式对话 - 实时返回文本片段"""
        
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages
        
        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": True,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-App-Id": self.config.app_id
        }
        
        try:
            async with self.client.stream(
                "POST",
                self.config.base_url,
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                                self.total_tokens_used += len(content)
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            raise Exception(f"流式调用失败: {str(e)}")
    
    async def structured_output(
        self,
        messages: List[Dict[str, str]],
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """结构化输出 - 强制返回JSON"""
        
        schema_instruction = f"""
请严格按照以下JSON格式返回，不要包含任何其他文字：
{json.dumps(output_schema, ensure_ascii=False, indent=2)}
"""
        
        if system_prompt:
            full_system = f"{system_prompt}\n\n{schema_instruction}"
        else:
            full_system = f"你是一个结构化数据生成助手。\n\n{schema_instruction}"
        
        result = await self.chat(messages, system_prompt=full_system)
        
        try:
            content = result["content"].strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            return {**parsed, "_meta": {"tokens_used": result["tokens_used"]}}
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {e}\n原始内容: {result['content'][:500]}")
    
    async def close(self):
        await self.client.aclose()


# 全局单例
_llm_service: Optional[XingHuoLLMService] = None


async def get_llm_service() -> XingHuoLLMService:
    global _llm_service
    if _llm_service is None:
        from config import settings
        config = LLMConfig(
            api_key=settings.XUNFEI_API_KEY,
            app_id=settings.XUNFEI_APP_ID,
            api_secret=settings.XUNFEI_API_SECRET,
            model=settings.LLM_MODEL
        )
        _llm_service = XingHuoLLMService(config)
    return _llm_service
```

---

## 🤖 第三步：创建7个专业Agent

每个Agent遵循统一模板：

### Agent模板结构

```python
# agents/xxx_agent.py
from typing import Dict, Any
from graph.state import AgentState
from services.llm_service import get_llm_service
import time
import logging

logger = logging.getLogger(__name__)


class XxxAgent:
    """
    Agent名称：xxx
    职责：一句话描述
    输入：从state中读取的字段
    输出：写入state的字段
    """
    
    AGENT_NAME = "xxx_agent"  # 唯一标识符
    
    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        标准接口 - 所有Agent必须实现
        
        Args:
            state: 完整的共享状态
            
        Returns:
            只包含要更新的字段字典（LangGraph自动合并）
        """
        start_time = time.time()
        
        try:
            logger.info(f"[{self.AGENT_NAME}] 开始处理...")
            
            # 1. 从state中读取所需数据
            input_data = self._extract_input(state)
            
            # 2. 执行业务逻辑（调用大模型等）
            output_data = await self._process(input_data)
            
            # 3. 构建返回结果
            result = self._build_result(output_data)
            
            # 4. 记录执行日志
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
        """从状态中提取输入数据 - 子类实现"""
        raise NotImplementedError
    
    async def _process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """核心处理逻辑 - 子类实现"""
        raise NotImplementedError
    
    def _build_result(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建返回结果 - 子类实现"""
        raise NotImplementedError
```

### Agent 1：ProfileAgent - 画像构建

```python
# agents/profile_agent.py
class ProfileAgent:
    """通过对话抽取学生特征，构建≥6维度的动态画像"""
    
    AGENT_NAME = "profile_agent"
    
    def _extract_input(self, state):
        return {
            "messages": state.get("messages", []),
            "user_query": state.get("user_query", ""),
            "existing_profile": state.get("student_profile")
        }
    
    async def _process(self, input_data):
        llm = await get_llm_service()
        
        prompt = f"""你是一个学习画像分析专家。根据学生的对话记录和最新提问，
分析并提取学生的10个维度特征。

对话历史：
{input_data['messages']}

最新问题：{input_data['user_query']}

{"已有画像（如有更新请调整）：" + str(input_data['existing_profile']) if input_data['existing_profile'] else "这是首次构建画像"}

请以JSON格式返回以下字段：
{{
    "major": "专业（如计算机科学、人工智能、电子信息等）",
    "grade_level": "年级（大一/大二/大三/大四/研究生）",
    "math_foundation": 数学基础评分(1-5),
    "programming_exp": 编程经验评分(1-5),
    "ml_knowledge": 机器学习知识评分(1-5),
    "learning_style": "学习风格(visual视觉型/auditory听觉型/kinesthetic动手型)",
    "learning_goal": "学习目标描述",
    "weak_points": ["薄弱点1", "薄弱点2"],
    "weekly_hours": 每周可投入小时数(数字),
    "interests": ["兴趣方向1"],
    "preferred_language": "偏好编程语言(Python/R/Java等)"
}}

注意：如果是对话中途，只需更新变化的字段，保持其他字段不变。
"""
        
        result = await llm.structured_output(
            messages=[{"role": "user", "content": prompt}],
            output_schema={
                "major": "", "grade_level": "",
                "math_foundation": 3, "programming_exp": 3, "ml_knowledge": 3,
                "learning_style": "", "learning_goal": "",
                "weak_points": [], "weekly_hours": 10,
                "interests": [], "preferred_language": ""
            },
            system_prompt="你是教育心理学专家，擅长通过对话分析学生学习特征。"
        )
        
        return {"profile": result}
    
    def _build_result(self, output_data):
        return {
            "student_profile": output_data["profile"],
            "profile_confidence": 0.85  # 可根据对话轮次动态调整
        }
```

### Agent 2：DocumentAgent - 文档生成

```python
# agents/document_agent.py
class DocumentAgent:
    """根据知识点和学生画像生成个性化讲解文档(Markdown)"""
    
    AGENT_NAME = "document_agent"
    
    def _extract_input(self, state):
        return {
            "topic": state.get("user_query", ""),
            "profile": state.get("student_profile"),
            "messages": state.get("messages", [])
        }
    
    async def _process(self, input_data):
        llm = await get_llm_service()
        profile = input_data["profile"] or {}
        
        prompt = f"""你是一位{profile.get('major', '计算机科学')}专业的资深教学专家。
为以下学生生成关于「{input_data['topic']}」的个性化讲解文档。

学生画像：
- 年级：{profile.get('grade_level', '未知')}
- 数学基础：{profile.get('math_foundation', 3)}/5 {'(较弱，需要更多基础解释)' if profile.get('math_foundation', 3) <= 2 else '(良好，可以深入)'}
- 编程经验：{profile.get('programming_exp', 3)}/5
- 学习风格：{profile.get('learning_style', '综合型')}
- 薄弱点：{', '.join(profile.get('weak_points', ['未知']))}
- 兴趣方向：{', '.join(profile.get('interests', []))}

要求（严格按Markdown格式）：
1. # 标题：知识点名称
2. ## 概念解释：用通俗易懂的语言解释（根据学生基础调整深度）
3. ## 数学原理：公式推导（基础差就简化，基础好则详细）
4. ## 代码示例：用{profile.get('preferred_language', 'Python')}编写完整可运行代码
5. ## 实际应用：结合{', '.join(profile.get('interests', ['通用场景']))}的应用案例
6. ## 常见误区：列出初学者容易犯的错误
7. ## 总结与思考题：2-3个引导性问题

字数要求：2000-3000字
语言风格：{'轻松活泼' if profile.get('grade_level') in ['大一', '大二'] else '严谨专业'}
"""
        
        result = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=f"你擅长将复杂概念简单化，特别擅长为{profile.get('grade_level', '')}学生定制教学内容。"
        )
        
        return {
            "content": result["content"],
            "title": input_data["topic"],
            "topic": input_data["topic"],
            "difficulty": self._assess_difficulty(profile),
            "estimated_time": len(result["content"]) // 15,  # 假设每分钟读15字
            "tags": [input_data["topic"], profile.get("major", "")]
        }
    
    def _assess_difficulty(self, profile):
        level = profile.get("ml_knowledge", 3) if profile else 3
        if level <= 2:
            return "beginner"
        elif level <= 4:
            return "intermediate"
        else:
            return "advanced"
    
    def _build_result(self, output_data):
        return {"document": output_data}
```

### Agent 3-7 的快速模板

按照相同模式创建其余Agent：

| Agent文件名 | 类名 | 核心职责 | 输出字段 |
|------------|------|---------|---------|
| `question_agent.py` | QuestionAgent | 生成练习题 | `questions` |
| `mindmap_agent.py` | MindmapAgent | 生成思维导图Markdown | `mindmap` |
| `code_agent.py` | CodeAgent | 生成代码实操案例 | `code_examples` |
| `path_agent.py` | PathAgent | 规划学习路径 | `learning_path` |
| `tutor_agent.py` | TutorAgent | 智能答疑辅导 | `tutor_response` |

每个Agent的核心逻辑都是：
1. 从`state`中读取`user_query`和`student_profile`
2. 构建针对该Agent的专业Prompt
3. 调用`llm_service`获取大模型输出
4. 返回对应字段

---

## 🔄 第四步：构建LangGraph工作流

### 文件：`backend/graph/workflow.py`

```python
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
    workflow.add_node("analyze_intent", intent_router_node)      # 意图识别
    workflow.add_node("build_profile", profile_agent)            # 画像构建
    workflow.add_node("generate_doc", doc_agent)                 # 文档生成
    workflow.add_node("generate_questions", question_agent)      # 题目生成
    workflow.add_node("generate_mindmap", mindmap_agent)         # 思维导图
    workflow.add_node("generate_code", code_agent)               # 代码案例
    workflow.add_node("plan_path", path_agent)                   # 路径规划
    workflow.add_node("tutor_answer", tutor_agent)               # 智能辅导
    workflow.add_node("final_summary", summary_generator_node)   # 最终总结
    
    # ===== 设置入口 =====
    workflow.set_entry_point("analyze_intent")
    
    # ===== 条件路由函数 =====
    def route_by_intent(state: AgentState) -> str:
        """根据用户意图决定走哪个分支"""
        intent = state.get("user_intent", "learn")
        
        logger.info(f"[Router] 用户意图: {intent}")
        
        if intent == "learn":
            # 完整学习流程
            return "build_profile"
        elif intent == "practice":
            # 练习模式：画像 → 题目
            return "build_profile_practice"
        elif intent == "ask_tutor":
            # 辅导模式：画像 → 辅导
            return "build_profile_tutor"
        elif intent == "view_path":
            # 查看路径：直接查路径
            return "plan_path_direct"
        else:
            return "build_profile"
    
    # ===== 添加条件边 =====
    workflow.add_conditional_edges(
        "analyze_intent",
        route_by_intent,
        {
            "build_profile": "build_profile",
            "build_profile_practice": "build_profile",
            "build_profile_tutor": "build_profile",
            "plan_path_direct": "plan_path"
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
    
    # ===== 练习模式边 =====
    workflow.add_edge("build_profile_practice", "generate_questions")
    workflow.add_edge("generate_questions", "final_summary")
    
    # ===== 辅导模式边 =====
    workflow.add_edge("build_profile_tutor", "tutor_answer")
    workflow.add_edge("tutor_answer", "final_summary")
    
    # ===== 编译图 =====
    memory = MemorySaver()  # 支持状态持久化和断点续传
    app = workflow.compile(checkpointer=memory)
    
    logger.info("[Workflow] 图编译完成")
    return app


# ===== 辅助节点函数 =====

async def intent_router_node(state: AgentState) -> dict:
    """意图识别节点 - 使用LLM判断用户想做什么"""
    from services.llm_service import get_llm_service
    
    llm = await get_llm_service()
    
    prompt = f"""分析用户的意图，返回以下之一：
- learn: 想学习新知识/新概念
- practice: 想做练习题/测试
- ask_tutor: 有具体问题需要解答
- view_path: 想查看/修改学习计划

用户输入：{state.get('user_query', '')}
上下文：{state.get('messages', [])[-3:] if state.get('messages') else '无'}

只返回意图关键词，不要解释。"""
    
    result = await llm.chat([{"role": "user", "content": prompt}])
    intent = result["content"].strip().lower()
    
    # 校验意图
    valid_intents = ["learn", "practice", "ask_tutor", "view_path"]
    if intent not in valid_intents:
        intent = "learn"  # 默认
    
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
    thread_id: str = "default"
) -> dict:
    """
    执行多Agent工作流（主入口）
    
    Args:
        user_query: 用户输入
        chat_history: 对话历史 [{"role": "user/content", ...}]
        thread_id: 会话ID（用于状态恢复）
    
    Returns:
        最终状态字典
    """
    graph = create_learning_graph()
    
    initial_state: AgentState = {
        "messages": chat_history,
        "user_query": user_query,
        "user_intent": "",
        "student_profile": None,
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
    
    # 执行工作流
    final_state = None
    async for event in graph.astream(initial_state, config=config):
        node_name = list(event.keys())[0]
        logger.info(f"[Workflow] 节点 '{node_name}' 完成")
        yield event  # 可用于实时推送给前端显示进度
    
    return final_state
```

---

## 🌐 第五步：FastAPI接口层

### 文件：`backend/app.py`

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import asyncio
from config import settings
from graph.workflow import create_learning_graph, execute_workflow
import uvicorn

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="基于LangGraph的多智能体个性化学习系统"
)

# CORS中间件（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 数据模型 =====

class ChatMessage(BaseModel):
    role: str  # user/assistant/system
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    thread_id: str = "default"


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


# ===== API端点 =====

@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "register": "/api/auth/register",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "llm_configured": bool(settings.XUNFEI_API_KEY)}


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    """用户注册"""
    # TODO: 实现真实注册逻辑（密码哈希、数据库存储）
    return {
        "success": True,
        "message": "注册成功",
        "user_id": f"user_{req.username}"
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    非流式对话接口 - 一次性返回完整结果
    
    适用场景：
    - 不需要实时展示进场的简单请求
    - API测试
    """
    try:
        history_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]
        
        final_state = None
        async for state in execute_workflow(
            user_query=request.message,
            chat_history=history_dicts,
            thread_id=request.thread_id
        ):
            final_state = state
        
        # 提取最终结果
        return {
            "success": True,
            "data": {
                "profile": final_state.get("student_profile"),
                "document": final_state.get("document"),
                "questions": final_state.get("questions"),
                "mindmap": final_state.get("mindmap"),
                "code_examples": final_state.get("code_examples"),
                "learning_path": final_state.get("learning_path"),
                "tutor_response": final_state.get("tutor_response"),
                "summary": final_state.get("final_summary"),
                "execution_log": final_state.get("execution_log", []),
                "errors": final_state.get("errors", [])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口 - SSE实时推送Agent执行过程
    
    返回的事件类型：
    - agent_start: Agent开始工作
    - agent_content: 内容片段（打字机效果）
    - agent_complete: Agent完成
    - error: 错误信息
    - done: 全部完成
    """
    
    async def event_generator():
        try:
            history_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in request.history
            ]
            
            async for event in execute_workflow(
                user_query=request.message,
                chat_history=history_dicts,
                thread_id=request.thread_id
            ):
                node_name = list(event.keys())[0]
                node_output = event[node_name]
                
                # 发送Agent开始事件
                yield f"data: {json.dumps({
                    'type': 'agent_start',
                    'agent': node_name,
                    'timestamp': asyncio.get_event_loop().time()
                }, ensure_ascii=False)}\n\n"
                
                # 如果有内容输出（如文档生成中的流式内容）
                if isinstance(node_output, dict):
                    for key in ['document', 'questions', 'mindmap', 'code_examples']:
                        if key in node_output and node_output[key]:
                            yield f"data: {json.dumps({
                                'type': 'agent_content',
                                'agent': node_name,
                                'resource_type': key,
                                'preview': str(node_output[key])[:200]
                            }, ensure_ascii=False)}\n\n"
                
                # 发送Agent完成事件
                yield f"data: {json.dumps({
                    'type': 'agent_complete',
                    'agent': node_name,
                    'status': 'success'
                }, ensure_ascii=False)}\n\n"
                
                # 模拟处理延迟（让前端有时间展示动画）
                await asyncio.sleep(0.1)
            
            # 全部完成
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
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


if __name__ == "__main__":
    print(f"🚀 启动 {settings.APP_NAME} v{settings.VERSION}")
    print(f"📍 地址: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 API文档: http://{settings.HOST}:{settings.PORT}/docs")
    
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
```

---

## 🎨 第六步：前端对接改造指南

### 6.1 创建API对接层

在`frontend/scripts/api.js`（或你的JS目录下）新增：

```javascript
// API配置
const API_BASE_URL = "http://localhost:8000";  // 后端地址

// 通用请求封装
class MLApiClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
        this.threadId = this.generateThreadId();
    }

    generateThreadId() {
        // 从localStorage读取或生成新的
        let tid = localStorage.getItem('ml_thread_id');
        if (!tid) {
            tid = 'thread_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ml_thread_id', tid);
        }
        return tid;
    }

    // 非流式对话
    async chat(message, history = []) {
        const response = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: history.map(msg => ({
                    role: msg.role,
                    content: msg.content
                })),
                thread_id: this.threadId
            })
        });

        const data = await response.json();
        if (!data.success) throw new Error(data.detail || '请求失败');
        return data.data;
    }

    // 流式对话（带Agent状态可视化）
    async chatStream(message, history = {}, onAgentStart, onAgentComplete, onContent, onError, onDone) {
        const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: Array.isArray(history) ? history.map(m => ({ role: m.role, content: m.content })) : [],
                thread_id: this.threadId
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.startsWith('data: '));

            for (const line of lines) {
                try {
                    const data = JSON.parse(line.slice(6));

                    switch (data.type) {
                        case 'agent_start':
                            if (onAgentStart) onAgentStart(data.agent);
                            break;
                        case 'agent_content':
                            if (onContent) onContent(data.agent, data.resource_type, data.preview);
                            break;
                        case 'agent_complete':
                            if (onAgentComplete) onAgentComplete(data.agent, data.status);
                            break;
                        case 'error':
                            if (onError) onError(data.message);
                            break;
                        case 'done':
                            if (onDone) onDone();
                            break;
                    }
                } catch (e) {
                    console.error('SSE解析错误:', e);
                }
            }
        }
    }

    // 用户注册
    async register(username, password, email) {
        const response = await fetch(`${this.baseUrl}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email })
        });
        return response.json();
    }
}

// 全局实例
const apiClient = new MLApiClient();
```

### 6.2 改造现有页面示例

#### 示例1：改造 `profile.html`（画像收集页面）

**原来**（纯前端预设逻辑）：
```javascript
// 旧代码 - 硬编码逻辑
function analyzeResponse(answer) {
    if (answer.includes("Python")) {
        userProfile.programming_exp = 4;
    }
    // ... 更多if-else
}
```

**改为**（调用后端AI分析）：
```javascript
// 新代码 - 调用真实AI
async function analyzeWithAI(userMessage) {
    // 显示加载状态
    showLoadingIndicator();

    // 调用后端流式API
    await apiClient.chatStream(
        userMessage,
        chatHistory,
        
        // Agent开始回调
        (agentName) => {
            updateAgentStatusUI(agentName, 'working');
            appendToChat(`🤖 ${getAgentDisplayName(agentName)} 正在分析...`);
        },
        
        // Agent完成回调
        (agentName, status) => {
            updateAgentStatusUI(agentName, 'completed');
        },
        
        // 内容回调
        (agentName, resourceType, preview) => {
            if (resourceType === 'profile') {
                updateProfileDisplay(preview);
            }
        },
        
        // 错误回调
        (error) => {
            showError(error);
        },
        
        // 完成回调
        () => {
            hideLoadingIndicator();
            showNextQuestion();
        }
    );
}
```

#### 示例2：添加Agent状态监控面板

在你的HTML页面中添加：

```html
<!-- Agent协作可视化面板 -->
<div id="agent-monitor-panel" style="display:none;">
    <h3>🤖 多智能体协作状态</h3>
    <div class="agent-grid">
        <!-- 7个Agent状态卡片 -->
        <div class="agent-card" id="card-profile">
            <div class="agent-icon">👤</div>
            <div class="agent-name">画像Agent</div>
            <div class="status idle">待命中</div>
        </div>
        <div class="agent-card" id="card-document">
            <div class="agent-icon">📝</div>
            <div class="agent-name">文档Agent</div>
            <div class="status idle">待命中</div>
        </div>
        <div class="agent-card" id="card-question">
            <div class="agent-icon">❓</div>
            <div class="agent-name">题库Agent</div>
            <div class="status idle">待命中</div>
        </div>
        <div class="agent-card" id="card-mindmap">
            <div class="agent-icon">🗺️</div>
            <div class="agent-name">导图Agent</div>
            <div class="status idle">待命中</div>
        </div>
        <div class="agent-card" id="card-code">
            <div class="agent-icon">💻</div>
            <div class="agent-name">代码Agent</div>
            <div class="status idle">待命中</div>
        </div>
        <div class="agent-card" id="card-path">
            <div class="agent-icon">🛤️</div>
            <div class="agent-name">路径Agent</div>
            <div class="status idle">待命中</div>
        </div>
        <div class="agent-card" id="card-tutor">
            <div class="agent-icon">🎓</div>
            <div class="agent-name">辅导Agent</div>
            <div class="status idle">待命中</div>
        </div>
    </div>
    
    <!-- 执行流程 -->
    <div class="workflow-flow">
        <span class="step active">① 输入</span> →
        <span class="step">② 画像</span> →
        <span class="step">③ 生成</span> →
        <span class="step">④ 规划</span> →
        <span class="step">⑤ 完成</span>
    </div>
</div>

<style>
.agent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin: 20px 0;
}

.agent-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    transition: all 0.3s ease;
}

.agent-card .agent-icon {
    font-size: 32px;
    margin-bottom: 8px;
}

.agent-card .status {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 20px;
    display: inline-block;
    margin-top: 8px;
}

.status.idle { background: #f0f0f0; color: #666; }
.status.working { 
    background: linear-gradient(135deg, #667eea, #764ba2); 
    color: white; 
    animation: pulse 1.5s infinite;
}
.status.completed { background: #00b894; color: white; }
.status.error { background: #e74c3c; color: white; }

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.7; transform: scale(1.05); }
}

.workflow-flow {
    text-align: center;
    font-size: 14px;
    color: #666;
    margin-top: 16px;
}

.step { padding: 4px 12px; border-radius: 4px; }
.step.active { background: #667eea; color: white; }
</style>

<script>
const agentNames = {
    'profile_agent': '画像Agent',
    'document_agent': '文档Agent',
    'question_agent': '题库Agent',
    'mindmap_agent': '导图Agent',
    'code_agent': '代码Agent',
    'path_agent': '路径Agent',
    'tutor_agent': '辅导Agent'
};

function getAgentDisplayName(agentKey) {
    return agentNames[agentKey] || agentKey;
}

function updateAgentStatusUI(agentName, status) {
    const cardId = 'card-' + agentName.replace('_agent', '');
    const card = document.getElementById(cardId);
    if (card) {
        const statusEl = card.querySelector('.status');
        statusEl.className = 'status ' + status;
        statusEl.textContent = {
            'idle': '待命中',
            'working': '工作中...',
            'completed': '已完成',
            'error': '出错'
        }[status] || status;
    }
}

function showAgentMonitor() {
    document.getElementById('agent-monitor-panel').style.display = 'block';
}
</script>
```

---

## 🗂️ 第七步：环境配置

### 创建 `.env` 文件

```bash
# 在项目根目录创建 .env 文件
```

```env
# 应用配置
APP_NAME=ML Learning Agent System
DEBUG=True

# 服务器
HOST=0.0.0.0
PORT=8000

# 讯飞星火配置 【必须填写 - 从 https://www.xfyun.cn/ 获取】
XUNFEI_API_KEY=你的API密钥
XUNFEI_APP_ID=你的APP_ID
XUNFEI_API_SECRET=你的API密钥

# 模型选择
LLM_MODEL=X2  # 推荐: X2 或 4.0-turbo

# 安全密钥（生产环境务必更改）
SECRET_KEY=your-super-secret-key-change-in-production-2024

# CORS（允许的前端地址）
CORS_ORIGINS=["http://localhost:5500","http://127.0.0.1:5500","http://localhost:3000"]
```

---

## 🚀 第八步：启动与测试

### 8.1 安装依赖

```bash
cd backend
python -m venv venv

# Windows激活
venv\Scripts\activate

# Mac/Linux激活
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 8.2 启动后端服务

```bash
cd backend
python app.py
```

看到以下输出表示成功：
```
🚀 启动 ML Learning Agent System v1.0.0
📍 地址: http://0.0.0.0:8000
📖 API文档: http://0.0.0.0:8000/docs
```

### 8.3 测试API

**方式1：浏览器访问**
- 打开 http://localhost:8000/docs （Swagger UI自动文档）

**方式2：命令行测试**
```bash
# 测试健康检查
curl http://localhost:8000/api/health

# 测试非流式对话
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"我想学习线性回归","history":[],"thread_id":"test"}'

# 测试流式对话
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"帮我理解梯度下降","history":[]}'
```

### 8.4 启动前端

保持原有的前端启动方式不变（直接打开HTML文件或使用Live Server），确保前端能访问到 `http://localhost:8000` 后端服务即可。

---

## 📊 第九步：验证清单

完成后逐一确认：

### 后端验证
- [ ] `python app.py` 能正常启动无报错
- [ ] 访问 `http://localhost:8000/docs` 能看到API文档
- [ ] `/api/health` 返回 `{"status":"healthy"}`
- [ ] `.env` 中已填入真实的讯飞API Key
- [ ] `/api/chat` 接口能返回完整响应（包含7种资源）
- [ ] `/api/chat/stream` 接口能收到SSE事件流

### Agent验证
- [ ] ProfileAgent能从对话中提取≥6维度画像
- [ ] DocumentAgent能生成Markdown格式的讲解文档
- [ ] QuestionAgent能生成不同类型的练习题
- [ ] MindmapAgent能生成可用于Markmap渲染的内容
- [ ] CodeAgent能生成带注释的可运行代码
- [ ] PathAgent能生成有序的学习步骤列表
- [ ] TutorAgent能针对具体问题给出解答

### 前端验证
- [ ] 页面能成功调用后端API（无CORS错误）
- [ ] Agent状态面板能正确显示各Agent的工作状态
- [ ] 流式输出时有打字机效果
- [ ] 生成的文档能在前端正确渲染Markdown
- [ ] 思维导图能正常显示
- [ ] 旧有的localStorage功能已迁移到后端API

### 功能完整性
- [ ] 用户注册功能正常
- [ ] 画像收集页面调用真实AI分析
- [ ] 学习路径由PathAgent动态生成
- [ ] 练习题由QuestionAgent动态生成
- [ ] 学习报告数据来自后端计算
- [ ] 知识库资源由多个Agent协同生成

---

## 🎯 第十步：演示准备建议

### 必须准备的测试账号和数据

```python
# 测试数据示例 - 至少准备这些
test_users = [
    {
        "username": "student_cs_sophomore",
        "profile": {
            "major": "计算机科学与技术",
            "grade_level": "大二",
            "math_foundation": 4,
            "programming_exp": 3,
            "ml_knowledge": 2,
            "learning_style": "visual",
            "learning_goal": "掌握机器学习基础并能做简单项目",
            "weak_points": ["数学推导", "算法优化"],
            "weekly_hours": 15,
            "interests": ["自然语言处理", "推荐系统"],
            "preferred_language": "Python"
        }
    },
    # ... 再准备至少19个不同画像的学生
]

test_queries = [
    "我想学习机器学习的基础知识",
    "帮我理解什么是过拟合和欠拟合",
    "给我出几道关于决策树的练习题",
    "我不理解反向传播算法的数学原理",
    "帮我制定一个Python数据分析的学习计划",
    # ... 准备15+不同的查询场景
]
```

### 演示视频录制要点（≤7分钟）

1. **开场（30秒）**：展示项目标题和整体界面
2. **用户注册+画像构建（1分钟）**：展示对话式画像收集，Agent状态变化
3. **核心功能演示（3分钟）**：
   - 输入学习需求 → 展示7个Agent依次工作
   - 展示生成的文档、题目、思维导图、代码等资源
   - 展示学习路径规划
4. **智能辅导演示（1分钟）**：提出具体问题，展示Tutor Agent回答
5. **技术创新亮点（1分钟）**：
   - 强调LangGraph多智能体架构
   - 展示Agent协作可视化
   - 说明讯飞星火大模型的集成
6. **结尾（30秒）**：总结价值和创新点

---

## ⚠️ 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 启动报错 `ModuleNotFoundError` | 未安装依赖 | 运行 `pip install -r requirements.txt` |
| API调用返回401 | API Key无效 | 检查`.env`中的`XUNFEI_API_KEY`是否正确 |
| 前端CORS错误 | 后端未开启CORS | 检查`config.py`中的`CORS_ORIGINS`配置 |
| 流式输出无数据 | 浏览器缓冲 | 确保响应头包含`X-Accel-Buffering: no` |
| Agent执行超时 | 网络慢或模型响应慢 | 增加`timeout`值或使用更快的模型 |
| 中文乱码 | 编码问题 | 确保所有文件UTF-8编码，`ensure_ascii=False` |

---

## 📈 下一步行动清单

### 今天完成
- [ ] 创建`backend/`目录结构
- [ ] 创建`requirements.txt`并安装依赖
- [ ] 创建`.env`文件并填入讯飞API Key
- [ ] 创建`config.py`、`state.py`、`llm_service.py`

### 明天完成
- [ ] 实现7个Agent（先完成ProfileAgent和DocumentAgent）
- [ ] 实现`workflow.py`工作流
- [ ] 创建`app.py` FastAPI入口

### 后天完成
- [ ] 创建前端`api.js`对接层
- [ ] 改造`profile.html`调用真实AI
- [ ] 添加Agent状态监控面板UI

### 第4天完成
- [ ] 全流程联调测试
- [ ] 准备测试数据和演示场景
- [ ] 录制演示视频

---

## 💡 技巧提示

1. **开发时先用Mock数据**：如果暂时没有讯飞API Key，可以在`llm_service.py`中返回假数据进行前端调试
2. **逐步增加Agent**：先跑通1个Agent，再逐步添加其他Agent
3. **善用LangGraph的checkpoint**：可以保存中间状态，方便调试
4. **日志很重要**：在每个Agent的关键步骤加logger，方便定位问题
5. **前端渐进式改造**：不要一次性改所有页面，一个个来

---

## 🎓 总结

这个技能帮你完成了从**纯前端原型**到**生产级多智能体系统**的完整升级路径。核心改变：

```
Before: HTML/CSS/JS + localStorage + 硬编码逻辑
After:  FastAPI + LangGraph + 7 Agents + 讯飞星火 + SQLite + SSE流式
```

你现在拥有的是：
- ✅ 真实的大模型能力（不是假的AI）
- ✅ 多智能体协作架构（符合赛题核心要求）
- ✅ 流式输出体验（现代化交互）
- ✅ 数据安全保障（数据库替代浏览器存储）
- ✅ 可扩展的系统设计（易于添加新Agent和新功能）

**祝比赛顺利！💪**
