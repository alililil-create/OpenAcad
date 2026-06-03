"""
机器学习知识图谱 — 9 章 45 知识点，包含依赖关系、难度、学习建议
每个节点记录前置依赖和后续依赖，支持病根溯源和自适应学习路径推荐
"""

KNOWLEDGE_GRAPH = {
    "ml_overview": {
        "id": "ml_overview",
        "name": "机器学习概述",
        "difficulty": 1,
        "description": "机器学习定义与分类、监督/无监督/强化学习、数据划分、偏差-方差权衡",
        "icon": "🤖",
        "estimated_hours": 4,
        "depends_on": [],
        "knowledge_points": [
            {"id": "ml_definition", "name": "机器学习定义与分类", "difficulty": 1, "core": True},
            {"id": "supervised_unsupervised", "name": "监督/无监督/强化学习", "difficulty": 1, "core": True},
            {"id": "data_split", "name": "训练集/验证集/测试集", "difficulty": 1, "core": True},
            {"id": "bias_variance", "name": "偏差-方差权衡", "difficulty": 2, "core": True}
        ],
        "tags": ["基础", "必学"],
        "learning_tip": "这是机器学习的入门章节，帮你建立全局视野。理解偏差-方差权衡对后续学习至关重要。"
    },
    "math_foundation": {
        "id": "math_foundation",
        "name": "数学基础",
        "difficulty": 2,
        "description": "线性代数、概率统计、微积分、优化方法、信息论基础",
        "icon": "🔢",
        "estimated_hours": 10,
        "depends_on": ["ml_overview"],
        "knowledge_points": [
            {"id": "linear_algebra", "name": "线性代数", "difficulty": 2, "core": True},
            {"id": "probability_stats", "name": "概率统计", "difficulty": 2, "core": True},
            {"id": "calculus", "name": "微积分", "difficulty": 2, "core": True},
            {"id": "optimization", "name": "优化方法", "difficulty": 3, "core": True},
            {"id": "information_theory", "name": "信息论基础", "difficulty": 3, "core": False}
        ],
        "tags": ["基础", "必备"],
        "learning_tip": "这是所有机器学习算法的基础层，建议优先掌握。数学薄弱的话后面的推导会非常吃力。信息论对理解决策树和深度学习很有帮助。"
    },
    "programming": {
        "id": "programming",
        "name": "编程与数据处理",
        "difficulty": 2,
        "description": "Python编程、NumPy、Pandas、数据预处理、scikit-learn",
        "icon": "💻",
        "estimated_hours": 8,
        "depends_on": ["math_foundation"],
        "knowledge_points": [
            {"id": "python", "name": "Python语法", "difficulty": 1, "core": True},
            {"id": "numpy", "name": "NumPy", "difficulty": 2, "core": True},
            {"id": "pandas", "name": "Pandas", "difficulty": 2, "core": False},
            {"id": "data_preprocessing", "name": "数据预处理", "difficulty": 2, "core": True},
            {"id": "sklearn", "name": "scikit-learn", "difficulty": 2, "core": True}
        ],
        "tags": ["基础", "动手"],
        "learning_tip": "数学理论学完之后，用代码把公式实现一遍，两者互相印证。数据预处理是实战第一步，sklearn是ML工程标配。"
    },
    "supervised_learning": {
        "id": "supervised_learning",
        "name": "监督学习",
        "difficulty": 3,
        "description": "线性回归、逻辑回归、朴素贝叶斯、KNN、决策树、SVM、集成学习",
        "icon": "🎯",
        "estimated_hours": 24,
        "depends_on": ["math_foundation", "programming"],
        "knowledge_points": [
            {"id": "linear_regression", "name": "线性回归", "difficulty": 2, "core": True},
            {"id": "logistic_regression", "name": "逻辑回归", "difficulty": 3, "core": True},
            {"id": "naive_bayes", "name": "朴素贝叶斯", "difficulty": 2, "core": True},
            {"id": "knn", "name": "K近邻算法", "difficulty": 2, "core": True},
            {"id": "decision_tree", "name": "决策树", "difficulty": 3, "core": True},
            {"id": "svm", "name": "支持向量机", "difficulty": 4, "core": True},
            {"id": "ensemble", "name": "集成学习", "difficulty": 4, "core": True}
        ],
        "tags": ["核心", "必学"],
        "learning_tip": "这是机器学习的核心模块。建议按难度递增：线性回归→逻辑回归→朴素贝叶斯→KNN→决策树→SVM→集成学习。每个算法都亲自动手写一遍代码。"
    },
    "unsupervised_learning": {
        "id": "unsupervised_learning",
        "name": "无监督学习",
        "difficulty": 3,
        "description": "K-Means聚类、层次聚类、DBSCAN、PCA降维、t-SNE可视化",
        "icon": "🔍",
        "estimated_hours": 10,
        "depends_on": ["math_foundation", "programming"],
        "knowledge_points": [
            {"id": "kmeans", "name": "K-Means聚类", "difficulty": 2, "core": True},
            {"id": "hierarchical_clustering", "name": "层次聚类", "difficulty": 3, "core": False},
            {"id": "dbscan", "name": "DBSCAN密度聚类", "difficulty": 3, "core": False},
            {"id": "pca", "name": "PCA降维", "difficulty": 3, "core": True},
            {"id": "tsne", "name": "t-SNE可视化", "difficulty": 3, "core": False}
        ],
        "tags": ["核心", "必学"],
        "learning_tip": "和监督学习并行的模块，可以交叉学习。PCA需要线性代数基础，DBSCAN适合处理任意形状的簇。t-SNE是高维数据可视化的利器。"
    },
    "neural_networks": {
        "id": "neural_networks",
        "name": "神经网络基础",
        "difficulty": 4,
        "description": "感知机、反向传播、激活函数与优化器、深度学习框架",
        "icon": "🧠",
        "estimated_hours": 12,
        "depends_on": ["math_foundation", "supervised_learning"],
        "knowledge_points": [
            {"id": "perceptron", "name": "感知机", "difficulty": 2, "core": True},
            {"id": "backpropagation", "name": "反向传播", "difficulty": 4, "core": True},
            {"id": "activation_optimizer", "name": "激活函数与优化器", "difficulty": 3, "core": True},
            {"id": "dl_framework", "name": "深度学习框架", "difficulty": 3, "core": True}
        ],
        "tags": ["进阶", "核心"],
        "learning_tip": "深度学习需要扎实的数学基础（链式法则、矩阵运算）和监督学习的经验。掌握PyTorch或TensorFlow是实战必备技能。"
    },
    "deep_learning": {
        "id": "deep_learning",
        "name": "深度学习",
        "difficulty": 4,
        "description": "CNN、RNN/LSTM、Transformer与注意力机制、GAN、迁移学习",
        "icon": "🔥",
        "estimated_hours": 20,
        "depends_on": ["neural_networks"],
        "knowledge_points": [
            {"id": "cnn", "name": "CNN卷积网络", "difficulty": 4, "core": True},
            {"id": "rnn_lstm", "name": "RNN与LSTM", "difficulty": 4, "core": True},
            {"id": "transformer", "name": "Transformer与注意力机制", "difficulty": 5, "core": True},
            {"id": "gan", "name": "生成对抗网络", "difficulty": 5, "core": False},
            {"id": "transfer_learning", "name": "迁移学习与预训练", "difficulty": 4, "core": True}
        ],
        "tags": ["进阶", "热点"],
        "learning_tip": "Transformer是当前AI最核心的架构，务必深入理解自注意力机制。迁移学习是工业界标配做法，预训练模型微调能大幅节省训练成本。"
    },
    "model_evaluation": {
        "id": "model_evaluation",
        "name": "模型评估与调优",
        "difficulty": 3,
        "description": "过拟合与欠拟合、交叉验证、评估指标、正则化、特征工程、超参数调优",
        "icon": "📊",
        "estimated_hours": 12,
        "depends_on": ["supervised_learning"],
        "knowledge_points": [
            {"id": "overfitting", "name": "过拟合与欠拟合", "difficulty": 3, "core": True},
            {"id": "cross_validation", "name": "交叉验证", "difficulty": 3, "core": True},
            {"id": "metrics", "name": "评估指标", "difficulty": 2, "core": True},
            {"id": "regularization", "name": "正则化", "difficulty": 4, "core": True},
            {"id": "feature_engineering", "name": "特征工程", "difficulty": 3, "core": True},
            {"id": "hyperparameter_tuning", "name": "超参数调优", "difficulty": 3, "core": False}
        ],
        "tags": ["实战", "重要"],
        "learning_tip": "学会调参比会跑模型更重要。特征工程是ML工程师的核心竞争力，建议每学完一个算法就来做对应的评估练习。"
    },
    "advanced_interest": {
        "id": "advanced_interest",
        "name": "进阶方向",
        "difficulty": 5,
        "description": "NLP、计算机视觉、大语言模型、强化学习、推荐系统、MLOps",
        "icon": "🚀",
        "estimated_hours": 28,
        "depends_on": ["deep_learning", "model_evaluation"],
        "knowledge_points": [
            {"id": "nlp", "name": "自然语言处理", "difficulty": 5, "core": False},
            {"id": "cv", "name": "计算机视觉", "difficulty": 5, "core": False},
            {"id": "llm", "name": "大语言模型", "difficulty": 5, "core": True},
            {"id": "reinforcement_learning", "name": "强化学习", "difficulty": 5, "core": False},
            {"id": "recommendation", "name": "推荐系统", "difficulty": 4, "core": False},
            {"id": "mlops", "name": "MLOps", "difficulty": 4, "core": False}
        ],
        "tags": ["前沿", "选修"],
        "learning_tip": "大语言模型是当前最热方向，建议必学。根据兴趣选1-2个方向深入，NLP和CV是两大应用支柱，推荐系统是工业界最成熟的ML应用。"
    }
}

CHAPTER_ORDER = [
    "ml_overview",
    "math_foundation",
    "programming",
    "supervised_learning",
    "unsupervised_learning",
    "neural_networks",
    "deep_learning",
    "model_evaluation",
    "advanced_interest"
]


def get_knowledge_graph() -> dict:
    return KNOWLEDGE_GRAPH


def get_chapter_order() -> list:
    return CHAPTER_ORDER


def build_reverse_dependencies() -> dict:
    rev = {}
    for ch_id, ch in KNOWLEDGE_GRAPH.items():
        for dep in ch.get("depends_on", []):
            if dep not in rev:
                rev[dep] = []
            rev[dep].append(ch_id)
    return rev


def trace_root_cause(weak_chapter_id: str, chapter_scores: dict) -> dict:
    """
    病根溯源：分析某章节薄弱的原因，追溯到前置依赖
    """
    chapter = KNOWLEDGE_GRAPH.get(weak_chapter_id)
    if not chapter:
        return {"error": "未知章节"}

    depends_on = chapter.get("depends_on", [])
    dep_analysis = []
    for dep_id in depends_on:
        dep_ch = KNOWLEDGE_GRAPH.get(dep_id, {})
        dep_score = chapter_scores.get(dep_id, 0)
        dep_analysis.append({
            "id": dep_id,
            "name": dep_ch.get("name", dep_id),
            "score": dep_score,
            "level": "weak" if dep_score < 40 else "medium" if dep_score < 70 else "strong",
            "is_root_cause": dep_score < 40
        })

    root_causes = [d for d in dep_analysis if d["is_root_cause"]]
    current_score = chapter_scores.get(weak_chapter_id, 0)

    conclusion = ""
    if root_causes:
        names = "、".join([d["name"] for d in root_causes])
        conclusion = f"你的「{chapter['name']}」之所以学不好（掌握度 {current_score}%），很可能不是因为它本身难，而是因为前置的「{names}」基础不牢。建议先补前置基础，再回来学效果会好很多。"
    elif dep_analysis:
        all_strong = all(d["level"] == "strong" for d in dep_analysis)
        if all_strong:
            conclusion = f"你的前置基础都不错，但「{chapter['name']}」掌握度只有 {current_score}%。建议重点攻克本章节的核心知识点，多做练习题巩固。"
        else:
            conclusion = f"「{chapter['name']}」掌握度 {current_score}%，前置基础部分薄弱，建议同时加强前置模块的学习。"
    else:
        conclusion = f"「{chapter['name']}」没有前置依赖，掌握度 {current_score}%。建议从最基础知识开始重新梳理。"

    return {
        "chapter_id": weak_chapter_id,
        "chapter_name": chapter["name"],
        "current_score": current_score,
        "depends_on": dep_analysis,
        "root_causes": root_causes,
        "conclusion": conclusion
    }


def get_recommended_path(chapter_scores: dict) -> list:
    """
    根据各章节掌握度生成推荐学习路径
    """
    path = []
    for ch_id in CHAPTER_ORDER:
        ch = KNOWLEDGE_GRAPH.get(ch_id, {})
        score = chapter_scores.get(ch_id, 0)
        depends_on = ch.get("depends_on", [])

        prereq_status = "ready"
        prereq_weak = []
        for dep in depends_on:
            dep_score = chapter_scores.get(dep, 0)
            if dep_score < 40:
                prereq_status = "blocked"
                prereq_weak.append(dep)

        path.append({
            "id": ch_id,
            "name": ch.get("name", ch_id),
            "icon": ch.get("icon", "📌"),
            "difficulty": ch.get("difficulty", 3),
            "estimated_hours": ch.get("estimated_hours", 0),
            "score": score,
            "status": "mastered" if score >= 80 else "learning" if score >= 40 else "weak" if score > 0 else "not_started",
            "prereq_status": prereq_status,
            "prereq_weak": prereq_weak,
            "learning_tip": ch.get("learning_tip", ""),
            "depends_on": depends_on
        })

    return path