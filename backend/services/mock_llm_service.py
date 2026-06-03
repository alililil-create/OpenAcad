import json
import time
import logging
import random
from typing import AsyncGenerator, List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MockLLMService:
    """
    Mock 模式 LLM 服务 - 返回模拟数据用于演示
    
    功能：
    - 模拟真实AI的响应时间（1-3秒延迟）
    - 返回高质量的示例数据
    - 支持流式输出（逐字显示效果）
    """

    def __init__(self):
        self.total_tokens_used = 0
        self.mock_profiles = [
            {
                "major": "计算机科学与技术",
                "grade_level": "大二",
                "math_foundation": 4,
                "programming_exp": 3,
                "ml_knowledge": 2,
                "learning_style": "visual",
                "learning_goal": "掌握机器学习基础，能够独立完成简单的ML项目",
                "weak_points": ["数学推导", "特征工程", "模型调优"],
                "weekly_hours": 15,
                "interests": ["自然语言处理", "推荐系统", "计算机视觉"],
                "preferred_language": "Python"
            },
            {
                "major": "人工智能",
                "grade_level": "大三",
                "math_foundation": 5,
                "programming_exp": 4,
                "ml_knowledge": 3,
                "learning_style": "kinesthetic",
                "learning_goal": "深入理解深度学习算法，参与Kaggle竞赛",
                "weak_points": ["理论深度", "论文阅读", "创新思维"],
                "weekly_hours": 20,
                "interests": ["深度学习", "强化学习", "GAN"],
                "preferred_language": "Python"
            }
        ]

        self.mock_documents = {
            "机器学习基础": {
                "title": "机器学习基础入门指南",
                "topic": "机器学习基础",
                "difficulty": "beginner",
                "estimated_time": 25,
                "tags": ["机器学习", "入门", "Python"],
                "content": """# 机器学习基础入门指南

## 📚 概念解释

**机器学习 (Machine Learning, ML)** 是人工智能的一个子领域，它使计算机能够从数据中自动学习和改进，而无需进行明确的编程。

简单来说：**不是我们教计算机怎么做，而是让计算机自己学会怎么做。**

### 核心三要素
1. **数据 (Data)**: 学习的原料
2. **模型 (Model)**: 学习的方法
3. **算法 (Algorithm)**: 学习的规则

## 🧮 数学基础

### 1. 线性代数
- **向量与矩阵运算**: 数据的基本表示形式
- **特征值与特征分解**: PCA降维的基础

### 2. 微积分
- **导数**: 梯度下降优化
- **偏导数**: 多变量函数优化

### 3. 概率论
- **条件概率**: 贝叶斯分类器
- **分布**: 正态分布、伯努利分布

## 💻 Python代码示例

```python
# 使用scikit-learn实现线性回归
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import numpy as np

# 准备数据
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 6, 8, 10])

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 训练模型
model = LinearRegression()
model.fit(X_train, y_train)

# 预测
predictions = model.predict(X_test)
print(f"预测值: {predictions}")
print(f"准确率: {model.score(X_test, y_test):.2f}")

# 可视化
import matplotlib.pyplot as plt
plt.scatter(X, y, color='blue', label='实际值')
plt.plot(X, model.predict(X), color='red', label='预测线')
plt.legend()
plt.title('线性回归示例')
plt.show()
```

## 🎯 实际应用案例

### 案例1: 房价预测 🏠
使用历史房屋数据（面积、位置、房龄等）预测房价。

### 案例2: 垃圾邮件分类 📧
根据邮件内容判断是否为垃圾邮件。

### 案例3: 图像识别 🖼️
识别手写数字（MNIST数据集）。

## ⚠️ 常见误区

1. **误区**: 机器学习=深度学习
   - **真相**: ML是父集，DL是子集。不是所有问题都需要DL。

2. **误区**: 数据越多越好
   - **真相**: 质量比数量重要。脏数据会降低模型性能。

3. **误区**: 复杂模型一定更好
   - **真相**: Occam's Razor原则 - 在同等效果下选择更简单的模型。

## 📝 总结与思考题

### 核心要点回顾
✅ 机器学习的三大要素：数据、模型、算法  
✅ 监督学习 vs 无监督学习 vs 强化学习  
✅ 过拟合与欠拟合的概念  

### 思考题
1. 为什么说"没有免费的午餐"定理在机器学习中很重要？
2. 如何判断一个模型是过拟合还是欠拟合？
3. 特征工程为什么被称为"机器学习中最重要的部分"？

---
*本文适合大二/大三学生，预计阅读时间25分钟*
"""
            }
        }

        self.mock_questions = [
            {
                "id": "q1",
                "type": "choice",
                "question": "以下哪个不属于机器学习的三大范式？",
                "options": ["监督学习", "无监督学习", "半监督学习", "过度学习"],
                "answer": "D",
                "explanation": "机器学习的三大范式是：监督学习（有标签）、无监督学习（无标签）、强化学习（通过奖励机制学习）。",
                "difficulty": 2,
                "knowledge_point": "ML基本概念",
                "hints": ["思考一下哪些是最常见的学习方式", "其中一个选项听起来就不像正规术语"]
            },
            {
                "id": "q2",
                "type": "fill_blank",
                "question": "在梯度下降算法中，学习率(learning rate)过大会导致______问题？",
                "options": None,
                "answer": "震荡或不收敛",
                "explanation": "学习率过大会导致参数更新步长太大，可能在最小值附近来回震荡甚至发散；学习率过小则收敛速度很慢。",
                "difficulty": 3,
                "knowledge_point": "优化算法",
                "hints": ["想象下山时步子太大", "考虑极端情况：学习率=∞"]
            },
            {
                "id": "q3",
                "type": "coding",
                "question": "请用Python实现一个简单的KNN分类器（使用欧氏距离）",
                "options": None,
                "answer": """```python
import numpy as np
from collections import Counter

def euclidean_distance(x1, x2):
    return np.sqrt(np.sum((x1 - x2) ** 2))

class KNN:
    def __init__(self, k=3):
        self.k = k
        
    def fit(self, X, y):
        self.X_train = X
        self.y_train = y
        
    def predict(self, X):
        predictions = [self._predict(x) for x in X]
        return predictions
    
    def _predict(self, x):
        # 计算到所有训练点的距离
        distances = [euclidean_distance(x, x_train) for x_train in self.X_train]
        
        # 取最近的k个点
        k_indices = np.argsort(distances)[:self.k]
        k_nearest_labels = [self.y_train[i] for i in k_indices]
        
        # 投票决定类别
        most_common = Counter(k_nearest_labels).most_common(1)
        return most_common[0][0]

# 使用示例
if __name__ == "__main__":
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    
    data = load_iris()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    clf = KNN(k=3)
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)
    
    print(f"准确率: {accuracy_score(y_test, predictions):.2f}")
```""",
                "explanation": "KNN是最基础的分类算法之一，核心思想是'近朱者赤近墨者黑'——通过找到最近的k个邻居来投票决定类别。",
                "difficulty": 4,
                "knowledge_point": "KNN算法",
                "hints": ["先实现距离计算函数", "然后找最近邻", "最后投票"]
            },
            {
                "id": "q4",
                "type": "case_study",
                "question": "场景分析：某电商平台想为用户推荐商品，有以下方案，你会选择哪种并说明理由？\nA. 基于内容的推荐\nB. 协同过滤\nC. 混合推荐\nD. 随机推荐",
                "options": ["A", "B", "C", "D"],
                "answer": "C",
                "explanation": "混合推荐结合了多种方法的优点：基于内容推荐解决冷启动问题，协同过滤利用群体智慧。实际工业界（如Netflix、Amazon）都采用混合策略。",
                "difficulty": 4,
                "knowledge_point": "推荐系统",
                "hints": ["考虑新用户问题", "考虑数据稀疏性", "考虑实际落地难度"]
            },
            {
                "id": "q5",
                "type": "choice",
                "question": "关于正则化（L1/L2），下列说法错误的是？",
                "options": [
                    "L1正则化可以产生稀疏解（特征选择）",
                    "L2正则化可以防止过拟合",
                    "正则化强度越大越好",
                    "Lasso使用L1，Ridge使用L2"
                ],
                "answer": "C",
                "explanation": "正则化强度需要权衡：太大会导致欠拟合（模型过于简单），太小则无法有效防止过拟合。通常通过交叉验证选择最优的正则化系数λ。",
                "difficulty": 3,
                "knowledge_point": "正则化",
                "hints": ["考虑正则化的目的", "思考极端情况"]
            }
        ]

        self.mock_mindmap = """# 机器学习知识体系

## 核心概念
### 定义
- 人工智能的子领域
- 从数据中自动学习模式

### 分类
- 监督学习
  - 回归任务
  - 分类任务
- 无监督学习
  - 聚类
  - 降维
- 强化学习
  - Agent与环境交互
  - 奖励机制

## 数学基础
### 线性代数
- 向量运算
- 矩阵分解
- 特征值与特征向量

### 微积分
- 梯度
- 偏导数
- 链式法则

### 概率统计
- 条件概率
- 贝叶斯定理
- 常见分布

## 核心算法
### 线性模型
- 线性回归
- 逻辑回归
- SVM

### 决策树
- ID3/C4.5/CART
- 随机森林
- GBDT/XGBoost

### 神经网络
- MLP
- CNN（卷积）
- RNN/LSTM（序列）
- Transformer（注意力）

## 实践流程
### 1. 数据准备
- 收集
- 清洗
- 特征工程

### 2. 模型训练
- 划分数据集
- 选择算法
- 训练调参

### 3. 评估优化
- 交叉验证
- 性能指标
- 模型部署

## 工具框架
### Python生态
- NumPy/Pandas
- Scikit-learn
- TensorFlow/PyTorch

### 应用领域
- NLP
- CV
- 推荐系统
- 时间序列"""

        self.mock_code_examples = [
            {
                "title": "数据预处理完整流程",
                "language": "Python",
                "code": """import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns

# 1. 加载数据
df = pd.read_csv('student_scores.csv')
print(f"原始数据形状: {df.shape}")
print(df.head())

# 2. 缺失值处理
print("\\n缺失值统计:")
print(df.isnull().sum())

# 数值列用均值填充
numeric_cols = df.select_dtypes(include=[np.number]).columns
df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())

# 类别列用众数填充
categorical_cols = df.select_dtypes(include=['object']).columns
for col in categorical_cols:
    df[col] = df[col].fillna(df[col].mode()[0])

# 3. 异常值检测（IQR方法）
Q1 = df['score'].quantile(0.25)
Q3 = df['score'].quantile(0.75)
IQR = Q3 - Q1
outliers = df[(df['score'] < Q1 - 1.5*IQR) | 
                 (df['score'] > Q3 + 1.5*IQR)]
print(f"\\n检测到 {len(outliers)} 个异常值")

# 4. 特征编码
le = LabelEncoder()
df['gender_encoded'] = le.fit_transform(df['gender'])

# 5. 特征标准化
scaler = StandardScaler()
df[['study_hours_scaled']] = scaler.fit_transform(df[['study_hours']])

# 6. 划分训练集和测试集
X = df[['study_hours_scaled', 'gender_encoded', 'attendance']]
y = df['score']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\\n训练集大小: {len(X_train)}")
print(f"测试集大小: {len(X_test)}")

# 7. 相关性热力图可视化
plt.figure(figsize=(10, 8))
sns.heatmap(df.corr(), annot=True, cmap='coolwarm', center=0)
plt.title('特征相关性热力图')
plt.tight_layout()
plt.show()

print("\\n✅ 数据预处理完成！")""",
                "explanation": "这是机器学习项目中最关键的一步，数据质量直接决定模型上限。",
                "comments": [
                    "# 第1行: 导入必要的库",
                    "# 第7-9行: 查看数据基本信息",
                    "# 第12-18行: 检测并处理缺失值",
                    "# 第22-28行: 使用IQR方法检测异常值",
                    "# 第31-33行: 对分类变量进行标签编码",
                    "# 第36-37行: 标准化数值特征（均值为0，方差为1）",
                    "# 第40-44行: 划分80%训练集+20%测试集"
                ],
                "expected_output": "原始数据形状: (100, 5)\n训练集大小: 80\n测试集大小: 20\n✅ 数据预处理完成！",
                "prerequisites": ["Pandas基础", "NumPy操作", "统计学概念"],
                "complexity": "中级"
            },
            {
                "title": "手写数字识别（MNIST）",
                "language": "Python",
                "code": """import tensorflow as tf
from tensorflow import keras
import numpy as np
import matplotlib.pyplot as plt

# 1. 加载MNIST数据集
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

# 2. 数据预处理
x_train = x_train.reshape(-1, 28, 28, 1).astype('float32') / 255.0
x_test = x_test.reshape(-1, 28, 28, 1).astype('float32') / 255.0

y_train = keras.utils.to_categorical(y_train, 10)
y_test = keras.utils.to_categorical(y_test, 10)

print(f"训练集形状: {x_train.shape}")
print(f"测试集形状: {x_test.shape}")

# 3. 构建CNN模型
model = keras.Sequential([
    # 卷积层1
    keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    keras.layers.MaxPooling2D((2, 2)),
    
    # 卷积层2
    keras.layers.Conv2D(64, (3, 3), activation='relu'),
    keras.layers.MaxPooling2D((2, 2)),
    
    # 全连接层
    keras.layers.Flatten(),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dropout(0.5),
    keras.layers.Dense(10, activation='softmax')  # 10个数字类别
])

model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# 4. 训练模型
history = model.fit(
    x_train, y_train,
    epochs=5,
    batch_size=64,
    validation_data=(x_test, y_test),
    verbose=1
)

# 5. 评估模型
test_loss, test_acc = model.evaluate(x_test, y_test)
print(f"\\n测试集准确率: {test_acc:.4f}")

# 6. 可视化训练过程
plt.figure(figsize=(12, 4))

# 准确率曲线
plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='训练准确率')
plt.plot(history.history['val_accuracy'], label='验证准确率')
plt.title('模型准确率')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

# 损失曲线
plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='训练损失')
plt.plot(history.history['val_loss'], label='验证损失')
plt.title('模型损失')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.tight_layout()
plt.show()

# 7. 预测示例
predictions = model.predict(x_test[:5])
predicted_labels = np.argmax(predictions, axis=1)
true_labels = np.argmax(y_test[:5], axis=1)

print("\\n预测结果:")
for i in range(5):
    print(f"样本{i+1}: 预测={predicted_labels[i]}, 实际={true_labels[i]}")""",
                "explanation": "CNN在图像识别任务中表现优异，MNIST是计算机视觉领域的\"Hello World\"。",
                "comments": [
                    "# 第6-11行: 加载并归一化数据(0-1范围)",
                    "# 第14-29行: 构建CNN架构(卷积→池化→全连接)",
                    "# 第31-34行: 编译模型(Adam优化器+交叉熵损失)",
                    "# 第37-43行: 训练5个epoch",
                    "# 第46-47行: 在测试集上评估"
                ],
                "expected_output": "训练集形状: (60000, 28, 28, 1)\n测试集准确率: 0.9876\n预测结果:\n样本1: 预测=7, 实际=7",
                "prerequisites": ["TensorFlow/Keras", "CNN基础知识", "图像处理"],
                "complexity": "高级"
            }
        ]

        self.mock_learning_path = [
            {
                "step_number": 1,
                "topic": "Python数据处理基础",
                "description": "掌握NumPy、Pandas进行数据清洗和预处理",
                "resources": [
                    {"type": "文档", "title": "NumPy官方教程"},
                    {"type": "视频", "title": "Pandas实战30分钟"},
                    {"type": "练习", "title": "Kaggle泰坦尼克号数据集"}
                ],
                "estimated_hours": 15,
                "prerequisites": ["Python基础语法"],
                "status": "not_started"
            },
            {
                "step_number": 2,
                "topic": "机器学习数学基础",
                "description": "学习线性代数、微积分、概率统计的核心概念",
                "resources": [
                    {"type": "文档", "title": "3Blue1Brown线性代数"},
                    {"type": "视频", "title": "斯坦福CS229数学预备"},
                    {"type": "代码", "title": "Python实现矩阵运算"}
                ],
                "estimated_hours": 20,
                "prerequisites": ["高等数学基础"],
                "status": "not_started"
            },
            {
                "step_number": 3,
                "topic": "经典机器学习算法",
                "description": "深入理解并实践线性回归、决策树、SVM、K-means等",
                "resources": [
                    {"type": "文档", "title": "Scikit-learn官方文档"},
                    {"type": "项目", "title": "波士顿房价预测"},
                    {"type": "项目", "title": "鸢尾花分类"}
                ],
                "estimated_hours": 25,
                "prerequisites": ["Python数据处理", "数学基础"],
                "status": "not_started"
            },
            {
                "step_number": 4,
                "topic": "深度学习入门",
                "description": "神经网络原理、反向传播、CNN/RNN基础",
                "resources": [
                    {"type": "课程", "title": "吴恩达DeepLearning.ai"},
                    {"type": "框架", "title": "PyTorch/TensorFlow入门"},
                    {"type": "项目", "title": "手写数字识别(MNIST)"}
                ],
                "estimated_hours": 30,
                "prerequisites": ["经典ML算法", "微积分"],
                "status": "not_started"
            },
            {
                "step_number": 5,
                "topic": "实战项目与部署",
                "description": "端到端项目经验：数据收集→模型训练→部署上线",
                "resources": [
                    {"type": "平台", "title": "Kaggle竞赛"},
                    {"type": "工具", "title": "Docker容器化"},
                    {"type": "云服务", "title": "阿里云PAI/ AWS SageMaker"}
                ],
                "estimated_hours": 20,
                "prerequisites": ["深度学习基础", "软件工程"],
                "status": "not_started"
            }
        ]

        logger.info("[MockLLM] Mock服务初始化完成")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        cache_agent: Optional[str] = None,
        cache_chapter: Optional[str] = None,
        cache_stage: Optional[str] = None,
        cache_profile_hash: Optional[str] = None,
        cache_user_id: int = 0,
        use_cache: bool = True,
        write_cache: bool = True
    ) -> Dict[str, Any]:
        """模拟非流式对话"""
        start_time = time.time()
        
        # 模拟网络延迟（1-2秒）
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        user_msg = messages[-1]["content"] if messages else ""
        
        # 根据关键词返回不同的模拟回复
        if "题目" in user_msg or "练习题" in user_msg or "出题" in user_msg or ("测试题" in user_msg) or ("题库" in user_msg and "生成" in user_msg):
            mock_quiz = [
                {"id": "q1", "type": "choice", "question": "以下哪个不属于机器学习的三大范式？", "options": ["A. 监督学习", "B. 无监督学习", "C. 半监督学习", "D. 强化学习"], "answer": "C", "explanation": "机器学习的三大范式是：监督学习、无监督学习、强化学习。'半监督学习'是监督与无监督的结合，不属于基本范式。", "difficulty": 2, "knowledge_point": "ML基本概念", "doc_section_id": "SEC-01", "hints": ["思考哪些是最常见的学习方式"], "key_points": ["监督学习", "无监督学习", "强化学习"]},
                {"id": "q2", "type": "choice", "question": "关于梯度下降算法，学习率过大会导致什么问题？", "options": ["A. 收敛速度过慢", "B. 震荡或不收敛", "C. 过拟合", "D. 欠拟合"], "answer": "B", "explanation": "学习率过大会导致参数更新步长太大，可能在最小值附近来回震荡甚至发散。", "difficulty": 2, "knowledge_point": "优化算法", "doc_section_id": "SEC-02", "hints": ["想象下山时步子太大"], "key_points": ["震荡", "不收敛", "发散"]},
                {"id": "q3", "type": "judge", "question": "机器学习就是深度学习。", "options": ["正确", "错误"], "answer": "B", "explanation": "机器学习是人工智能的子领域，深度学习是机器学习的子集。不是所有机器学习问题都需要深度学习。", "difficulty": 1, "knowledge_point": "ML基本概念", "doc_section_id": "SEC-01", "hints": ["考虑包含关系"], "key_points": ["子集", "包含关系"]},
                {"id": "q4", "type": "judge", "question": "数据量越大，模型效果一定越好。", "options": ["正确", "错误"], "answer": "B", "explanation": "数据质量比数量更重要。脏数据、噪声数据反而会降低模型性能。", "difficulty": 1, "knowledge_point": "数据质量", "doc_section_id": "SEC-05", "hints": ["考虑数据质量"], "key_points": ["数据质量", "噪声", "脏数据"]},
                {"id": "q5", "type": "text", "question": "请简述监督学习和无监督学习的区别，并各举一个应用场景。", "options": None, "answer": "监督学习使用有标签的数据进行训练，目标是学习输入到输出的映射关系，常用于分类和回归任务，例如垃圾邮件分类。无监督学习使用无标签数据，发现数据中的隐藏结构或模式，常用于聚类和降维，例如客户分群。", "explanation": "监督学习依赖于标注数据，每个样本都有明确的正确答案；无监督学习则试图在没有标签的情况下发现数据内在规律。", "difficulty": 3, "knowledge_point": "监督学习vs无监督学习", "doc_section_id": "SEC-01", "hints": ["一个有标签一个无标签", "想想分类和聚类的区别"], "key_points": ["有标签", "无标签", "分类", "回归", "聚类"]},
            ]
            content = json.dumps(mock_quiz, ensure_ascii=False)
        elif "画像" in user_msg or "学习情况" in user_msg or "学习情况分析" in user_msg:
            content = f"已成功构建你的学习画像！\\n\\n基于你的对话，我提取了以下特征：\\n\\n📚 专业背景：{self.mock_profiles[0]['major']}\\n🎓 年级水平：{self.mock_profiles[0]['grade_level']}\\n🔢 数学基础：{self.mock_profiles[0]['math_foundation']}/5\\n💻 编程经验：{self.mock_profiles[0]['programming_exp']}/5\\n🤖 ML知识储备：{self.mock_profiles[0]['ml_knowledge']}/5\\n\\n接下来我将调用其他Agent为你生成个性化学习资源..."
        elif "文档" in user_msg or "讲解" in user_msg or ("教学" in user_msg and "生成" in user_msg):
            content = """# 机器学习基础 - 🌱 启蒙

## [SEC-01] 核心概念

**机器学习 (Machine Learning)** 是人工智能的一个子领域，它使计算机能够从数据中自动学习和改进，而无需进行明确的编程。

简单来说：不是我们教计算机怎么做，而是让计算机自己学会怎么做。

核心三要素：
1. **数据 (Data)**: 学习的原料
2. **模型 (Model)**: 学习的方法
3. **算法 (Algorithm)**: 学习的规则

## [SEC-02] 原理详解

机器学习的基本流程是：收集数据 → 选择模型 → 训练模型 → 评估模型 → 预测。

就像学骑自行车一样：你不需要记住每块肌肉该怎么动（编程），而是通过不断练习（数据+反馈），身体自然学会了平衡（模型）。

关键概念：
- **训练集**: 用来学习的数据
- **测试集**: 用来检验学习效果的数据
- **特征**: 数据中用来做判断的属性

## [SEC-03] 代码示例

```python
from sklearn.linear_model import LinearRegression
import numpy as np

X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 6, 8, 10])

model = LinearRegression()
model.fit(X, y)

predictions = model.predict([[6]])
print(f"预测值: {predictions}")
```

## [SEC-04] 应用场景

1. **房价预测**: 根据面积、位置等特征预测房价
2. **垃圾邮件分类**: 根据邮件内容判断是否为垃圾邮件
3. **图像识别**: 识别手写数字（MNIST数据集）
4. **推荐系统**: 根据用户行为推荐商品

## [SEC-05] 常见误区与总结

常见误区：
1. 机器学习≠深度学习，深度学习是机器学习的子集
2. 数据质量比数量更重要，脏数据会降低模型性能
3. 复杂模型不一定更好，Occam's Razor原则

总结：机器学习让计算机从数据中学习规律，三大要素是数据、模型和算法。"""
        else:
            content = f"[Mock回复] 你说的是：{user_msg}\\n\\n这是一个模拟的AI回复。在真实模式下，这里会调用大模型API生成个性化的回答。\\n\\n当前系统状态：\\n- ✅ 后端服务正常运行\\n- ✅ 7个Agent已就绪\\n- ⏳ 等待接入真实AI模型"

        processing_time = time.time() - start_time
        tokens_used = len(content)
        self.total_tokens_used += tokens_used

        return {
            "content": content,
            "tokens_used": tokens_used,
            "processing_time": processing_time,
            "model": "mock-model-v1.0"
        }

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """模拟流式输出"""
        result = await self.chat(messages, system_prompt)
        content = result["content"]
        
        # 模拟打字机效果：逐字符输出
        words = content.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words)-1 else "")
            await asyncio.sleep(0.03)  # 每个词间隔30ms

    async def structured_output(
        self,
        messages: List[Dict[str, str]],
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        cache_user_id: int = 0
    ) -> Dict[str, Any]:
        """模拟结构化输出"""
        await asyncio.sleep(1.5)  # 模拟处理时间
        
        # 根据请求返回对应的模拟数据
        if "major" in str(output_schema):  # 画像请求
            profile = self.mock_profiles[0]
            return {
                **profile,
                "_meta": {"tokens_used": 256}
            }
        else:
            return {
                "result": "mock_data",
                "_meta": {"tokens_used": 100}
            }

    async def simple_chat(self, message: str) -> str:
        result = await self.chat([{"role": "user", "content": message}])
        return result["content"]

    async def close(self):
        pass


# 全局单例
_mock_llm_service: Optional[MockLLMService] = None


async def get_llm_service():
    global _mock_llm_service
    if _mock_llm_service is None:
        _mock_llm_service = MockLLMService()
    return _mock_llm_service


# 导入asyncio（Mock服务需要）
import asyncio
