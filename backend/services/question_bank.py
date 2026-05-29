"""
机器学习题库 — 15 道单选题，覆盖 7 个章节，28 个知识点
支持自适应跳题逻辑
"""

# ===== 题库定义 =====
# 每道题包含: id, chapter, knowledge_points[], difficulty(1-5), question, options, answer(0-based), explanation

QUESTIONS = [
    # ===== 数学基础 (3题) =====
    {
        "id": "math_1",
        "chapter": "math_foundation",
        "knowledge_points": ["linear_algebra"],
        "difficulty": 2,
        "question": "在机器学习中，矩阵乘法的核心作用是什么？",
        "options": [
            "仅用于数据存储",
            "实现线性变换和特征空间映射",
            "替代向量加法",
            "用于数据归一化"
        ],
        "answer": 1,
        "explanation": "矩阵乘法对应线性变换，是神经网络前向传播和特征工程（如PCA）的数学基础。"
    },
    {
        "id": "math_2",
        "chapter": "math_foundation",
        "knowledge_points": ["probability_stats"],
        "difficulty": 3,
        "question": "朴素贝叶斯分类器的'朴素'假设是什么？",
        "options": [
            "假设所有样本数量相等",
            "假设特征之间相互独立",
            "假设先验概率为均匀分布",
            "假设所有特征服从正态分布"
        ],
        "answer": 1,
        "explanation": "朴素贝叶斯假设特征条件独立，即给定类别后各特征之间相互独立，大幅简化了计算。"
    },
    {
        "id": "math_3",
        "chapter": "math_foundation",
        "knowledge_points": ["calculus", "optimization"],
        "difficulty": 3,
        "question": "梯度下降算法中，梯度的方向代表什么？",
        "options": [
            "函数值下降最快的方向的反方向",
            "函数值上升最快的方向",
            "函数的等值线方向",
            "函数的二阶导数方向"
        ],
        "answer": 1,
        "explanation": "梯度指向函数值上升最快的方向，因此梯度下降中参数更新方向为负梯度方向，即下降最快的方向。"
    },

    # ===== 编程基础 (2题) =====
    {
        "id": "code_1",
        "chapter": "programming",
        "knowledge_points": ["python"],
        "difficulty": 2,
        "question": "以下 Python 列表推导式的输出是什么？\n```python\n[x**2 for x in range(5) if x % 2 == 0]\n```",
        "options": ["[0, 4, 8, 12, 16]", "[0, 1, 4, 9, 16]", "[0, 4, 16]", "[0, 2, 4]"],
        "answer": 2,
        "explanation": "x 取 0,1,2,3,4，仅偶数 0,2,4 通过条件筛选，平方得 [0, 4, 16]。"
    },
    {
        "id": "code_2",
        "chapter": "programming",
        "knowledge_points": ["numpy", "pandas"],
        "difficulty": 2,
        "question": "使用 Pandas 读取 CSV 文件并查看前5行的正确方法是？",
        "options": [
            "pd.read_csv('file.csv').top(5)",
            "pd.read('file.csv').head(5)",
            "pd.read_csv('file.csv').head(5)",
            "pd.open_csv('file.csv').preview(5)"
        ],
        "answer": 2,
        "explanation": "Pandas 读取 CSV 用 pd.read_csv()，查看前几行用 .head(n) 方法。"
    },

    # ===== 监督学习 (4题) =====
    {
        "id": "sup_1",
        "chapter": "supervised_learning",
        "knowledge_points": ["linear_regression", "logistic_regression"],
        "difficulty": 2,
        "question": "线性回归和逻辑回归最主要的区别是什么？",
        "options": [
            "线性回归只能处理一维数据",
            "逻辑回归用于分类问题，线性回归用于回归问题",
            "逻辑回归不需要训练",
            "线性回归使用梯度下降，逻辑回归不使用"
        ],
        "answer": 1,
        "explanation": "线性回归预测连续值（回归），逻辑回归通过 sigmoid 函数输出概率用于分类。"
    },
    {
        "id": "sup_2",
        "chapter": "supervised_learning",
        "knowledge_points": ["decision_tree"],
        "difficulty": 3,
        "question": "决策树节点划分时，ID3算法使用的准则是什么？",
        "options": [
            "基尼系数 (Gini Index)",
            "信息增益 (Information Gain)",
            "均方误差 (MSE)",
            "F1分数"
        ],
        "answer": 1,
        "explanation": "ID3 使用信息增益作为划分准则，选择使信息增益最大的特征进行分裂。C4.5 用信息增益率，CART 可用基尼系数。"
    },
    {
        "id": "sup_3",
        "chapter": "supervised_learning",
        "knowledge_points": ["svm"],
        "difficulty": 4,
        "question": "SVM 中核函数的核心作用是什么？",
        "options": [
            "加速模型训练",
            "将数据映射到高维空间使线性可分",
            "减少模型参数数量",
            "替代损失函数"
        ],
        "answer": 1,
        "explanation": "核函数通过隐式映射将低维不可分数据投影到高维空间，在高维空间寻找最优分离超平面。"
    },
    {
        "id": "sup_4",
        "chapter": "supervised_learning",
        "knowledge_points": ["ensemble"],
        "difficulty": 3,
        "question": "随机森林和GBDT的主要区别是什么？",
        "options": [
            "随机森林只能分类，GBDT只能回归",
            "随机森林是Bagging（并行），GBDT是Boosting（串行）",
            "它们是完全相同的算法",
            "随机森林比GBDT总是更准确"
        ],
        "answer": 1,
        "explanation": "随机森林用 Bagging 并行训练多棵决策树后投票/平均；GBDT 用 Boosting 串行训练，每棵树拟合前一棵的残差。"
    },

    # ===== 无监督学习 (1题) =====
    {
        "id": "unsup_1",
        "chapter": "unsupervised_learning",
        "knowledge_points": ["kmeans", "pca"],
        "difficulty": 3,
        "question": "关于K-means和PCA，以下说法正确的是？",
        "options": [
            "两者都是分类算法",
            "K-means用于聚类，PCA用于降维",
            "PCA需要标签，K-means不需要",
            "两者都属于监督学习"
        ],
        "answer": 1,
        "explanation": "K-means 是无监督聚类算法，PCA 是无监督降维方法，两者都不需要标签数据。"
    },

    # ===== 神经网络与深度学习 (2题) =====
    {
        "id": "nn_1",
        "chapter": "neural_networks",
        "knowledge_points": ["perceptron", "backpropagation"],
        "difficulty": 3,
        "question": "反向传播算法的核心思想是什么？",
        "options": [
            "随机初始化参数",
            "利用链式法则从输出层逐层向前计算梯度",
            "直接计算每一层的独立梯度",
            "使用随机搜索优化参数"
        ],
        "answer": 1,
        "explanation": "反向传播利用链式法则，从输出层开始逐层反向计算损失函数对各层参数的梯度，是神经网络训练的核心算法。"
    },
    {
        "id": "nn_2",
        "chapter": "neural_networks",
        "knowledge_points": ["cnn"],
        "difficulty": 3,
        "question": "CNN中卷积层的主要作用是提取哪种特征？",
        "options": [
            "全局语义特征",
            "局部空间特征（边缘、纹理等）",
            "时间序列特征",
            "类别标签"
        ],
        "answer": 1,
        "explanation": "卷积核在图像上滑动，提取局部空间特征（边缘、角点、纹理），深层卷积可提取更抽象的高级特征。"
    },

    # ===== 模型评估与调优 (2题) =====
    {
        "id": "eval_1",
        "chapter": "model_evaluation",
        "knowledge_points": ["overfitting", "regularization"],
        "difficulty": 3,
        "question": "当模型在训练集准确率很高但测试集准确率很低时，这种现象叫什么？如何缓解？",
        "options": [
            "欠拟合 — 增加模型复杂度",
            "过拟合 — 使用正则化、增加数据或简化模型",
            "正常现象 — 不需要处理",
            "数据泄露 — 重新划分数据集"
        ],
        "answer": 1,
        "explanation": "训练集高、测试集低是典型的过拟合。可通过 L1/L2 正则化、Dropout、数据增强、早停等策略缓解。"
    },
    {
        "id": "eval_2",
        "chapter": "model_evaluation",
        "knowledge_points": ["cross_validation", "metrics"],
        "difficulty": 2,
        "question": "K 折交叉验证的主要目的是什么？",
        "options": [
            "增加训练样本数量",
            "更可靠地评估模型泛化能力",
            "减少模型参数量",
            "加速模型训练"
        ],
        "answer": 1,
        "explanation": "K折交叉验证将数据分为K份轮换验证，每个样本都参与训练和验证，得到更稳定可靠的模型性能估计。"
    },

    # ===== 进阶方向兴趣探测 (1题) =====
    {
        "id": "adv_1",
        "chapter": "advanced_interest",
        "knowledge_points": ["nlp", "cv", "reinforcement_learning", "mlops"],
        "difficulty": 1,
        "question": "以下哪个机器学习子方向你最感兴趣或有过接触？",
        "options": [
            "自然语言处理 (NLP) — 文本分类、GPT等",
            "计算机视觉 (CV) — 图像识别、目标检测等",
            "强化学习 — 游戏AI、机器人控制等",
            "MLOps — 模型部署、监控、CI/CD"
        ],
        "answer": -1,  # 无正确/错误之分，兴趣探测题
        "explanation": "此题不计分，用于探测学习兴趣方向，帮助后续推荐学习内容。"
    }
]


# ===== 章节分配规则 =====
CHAPTER_ALLOCATION = {
    "math_foundation": {"total": 3, "required": 1},        # 第一题对则跳过剩余
    "programming": {"total": 2, "required": 1},
    "supervised_learning": {"total": 4, "required": 2},
    "unsupervised_learning": {"total": 1, "required": 1},
    "neural_networks": {"total": 2, "required": 1},
    "model_evaluation": {"total": 2, "required": 1},
    "advanced_interest": {"total": 1, "required": 1}       # 兴趣探测，必答
}

# 知识点→章节映射（用于score计算）
KNOWLEDGE_POINT_TO_CHAPTER = {}
for q in QUESTIONS:
    for kp in q["knowledge_points"]:
        KNOWLEDGE_POINT_TO_CHAPTER[kp] = q["chapter"]

# 所有28个知识点列表
ALL_KNOWLEDGE_POINTS = {
    "math_foundation": ["linear_algebra", "probability_stats", "calculus", "optimization"],
    "programming": ["python", "numpy", "pandas"],
    "supervised_learning": ["linear_regression", "logistic_regression", "decision_tree", "svm", "ensemble"],
    "unsupervised_learning": ["kmeans", "pca"],
    "neural_networks": ["perceptron", "backpropagation", "cnn", "rnn"],
    "model_evaluation": ["overfitting", "cross_validation", "metrics", "regularization"],
    "advanced_interest": ["nlp", "cv", "reinforcement_learning", "mlops"]
}


def get_questions_by_chapter(chapter: str) -> list:
    """获取某章节的所有题目"""
    return [q for q in QUESTIONS if q["chapter"] == chapter]


def get_question(question_id: str) -> dict | None:
    """根据 ID 获取题目详情"""
    for q in QUESTIONS:
        if q["id"] == question_id:
            return q
    return None


def get_all_chapters() -> list:
    """获取所有章节"""
    return list(CHAPTER_ALLOCATION.keys())


def get_chapter_names() -> dict:
    """章节英文→中文映射"""
    return {
        "math_foundation": "数学基础",
        "programming": "编程基础",
        "supervised_learning": "监督学习",
        "unsupervised_learning": "无监督学习",
        "neural_networks": "神经网络与深度学习",
        "model_evaluation": "模型评估与调优",
        "advanced_interest": "进阶方向（兴趣探测）"
    }