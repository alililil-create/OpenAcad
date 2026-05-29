// AI画像收集页逻辑

// 画像问题配置
const profileQuestions = [
  {
    id: 'foundation',
    question: '你的数学基础如何？',
    options: [
      { text: '基础薄弱，需要从基础补起', value: 1 },
      { text: '有一些数学基础，但需要巩固', value: 2 },
      { text: '数学基础扎实，可以直接学习', value: 3 },
      { text: '数学能力较强，可以深入学习', value: 4 },
      { text: '数学功底深厚，可以挑战高级内容', value: 5 }
    ]
  },
  {
    id: 'programming',
    question: '你的编程经验如何？',
    options: [
      { text: '完全没有编程经验', value: 1 },
      { text: '学过一点编程但不熟练', value: 2 },
      { text: '能够编写简单程序', value: 3 },
      { text: '有丰富编程经验', value: 4 },
      { text: '编程高手，可以快速实现想法', value: 5 }
    ]
  },
  {
    id: 'mlKnowledge',
    question: '你对机器学习的了解程度？',
    options: [
      { text: '完全不了解，只是听说过', value: 1 },
      { text: '知道一些概念，但没有实践过', value: 2 },
      { text: '有一些基础，了解常见算法', value: 3 },
      { text: '比较熟悉，能独立完成简单项目', value: 4 },
      { text: '非常精通，可以解决复杂问题', value: 5 }
    ]
  },
  {
    id: 'learningGoal',
    question: '你学习机器学习的主要目标是？',
    options: [
      { text: '拓宽知识面，了解AI时代趋势' },
      { text: '完成学业要求或考试' },
      { text: '转行进入AI相关领域' },
      { text: '提升现有工作能力' },
      { text: '创业或做AI相关项目' }
    ]
  },
  {
    id: 'timeAvailable',
    question: '你每天可以投入多少时间学习？',
    options: [
      { text: '不足1小时' },
      { text: '1-2小时' },
      { text: '2-3小时' },
      { text: '3-5小时' },
      { text: '5小时以上，可以全力投入' }
    ]
  },
  {
    id: 'preferredStyle',
    question: '你更喜欢哪种学习方式？',
    options: [
      { text: '理论为主，先打扎实基础' },
      { text: '实践为主，边做边学' },
      { text: '理论与实践结合' },
      { text: '视频教学为主' },
      { text: '项目驱动学习' }
    ]
  },
  {
    id: 'strongAreas',
    question: '你觉得自己比较擅长的领域是？（可多选）',
    options: [
      { text: '数学与逻辑' },
      { text: '编程开发' },
      { text: '数据分析' },
      { text: '业务理解' },
      { text: '科研学术' }
    ],
    multiSelect: true,
    minSelect: 1,
    maxSelect: 3
  },
  {
    id: 'weakAreas',
    question: '你觉得自己比较薄弱的领域是？（可多选）',
    options: [
      { text: '数学推导' },
      { text: '编程实现' },
      { text: '调参优化' },
      { text: '项目实战' },
      { text: '模型部署' }
    ],
    multiSelect: true,
    minSelect: 1,
    maxSelect: 3
  }
];

// 当前状态
let currentQuestionIndex = 0;
let userAnswers = {};
let selectedOptions = [];

// DOM元素
let chatContainer;
let progressBar;
let progressText;

document.addEventListener('DOMContentLoaded', async () => {
  chatContainer = document.getElementById('chatContainer');
  progressBar = document.getElementById('progressFill');
  progressText = document.getElementById('progressText');

  // 初始化：如果未注册，跳转到注册页
  if (!Storage.isRegistered()) {
    navigateTo('register.html');
    return;
  }

  // 如果已完成画像，跳转到首页
  if (Storage.isProfileCompleted()) {
    navigateTo('index.html');
    return;
  }

  // 开始画像收集流程
  await delay(500);
  await showQuestion();
});

// 显示当前问题
async function showQuestion() {
  const question = profileQuestions[currentQuestionIndex];
  updateProgress();

  // 创建唯一的ID前缀
  const qid = `q${currentQuestionIndex}`;

  // 显示AI问题消息
  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message ai';
  messageEl.innerHTML = `
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble">
      <div class="question-text typing-cursor" id="${qid}-text"></div>
      <div class="options-container" id="${qid}-options"></div>
    </div>
  `;
  chatContainer.appendChild(messageEl);

  // 滚动到底部
  chatContainer.scrollTop = chatContainer.scrollHeight;

  // 打字机效果显示问题
  const questionTextEl = document.getElementById(`${qid}-text`);
  await typeWriter(questionTextEl, question.question, 40);

  // 显示选项
  const optionsContainer = document.getElementById(`${qid}-options`);
  question.options.forEach((option, index) => {
    const optionBtn = document.createElement('button');
    optionBtn.className = 'option-btn';
    optionBtn.textContent = option.text;
    optionBtn.onclick = () => handleOptionSelect(option, index, question);
    optionBtn.style.animationDelay = `${index * 0.1}s`;
    optionBtn.classList.add('animate-fade-in-up');
    optionsContainer.appendChild(optionBtn);
  });

  // 如果是多选，添加确认按钮
  if (question.multiSelect) {
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.style.marginTop = '16px';
    confirmBtn.style.width = '100%';
    confirmBtn.textContent = '确认提交';
    confirmBtn.onclick = async () => {
      if (selectedOptions.length < question.minSelect) {
        showToast(`请至少选择${question.minSelect}项`, 'info');
        return;
      }
      userAnswers[question.id] = [...selectedOptions];

      // 显示用户选择
      await showUserMessage(selectedOptions.join('、'));

      // 清空已选项
      selectedOptions = [];

      // 下一题
      await delay(800);
      currentQuestionIndex++;

      if (currentQuestionIndex < profileQuestions.length) {
        await showQuestion();
      } else {
        await completeProfile();
      }
    };
    optionsContainer.appendChild(confirmBtn);
  }
}

// 处理选项选择
async function handleOptionSelect(option, index, question) {
  const qid = `q${currentQuestionIndex}`;
  const optionsContainer = document.getElementById(`${qid}-options`);
  const optionBtns = optionsContainer.querySelectorAll('.option-btn');

  // 如果是多选
  if (question.multiSelect) {
    optionBtns[index].classList.toggle('selected');

    // 更新已选选项
    const selectedIndex = selectedOptions.indexOf(option.text);
    if (selectedIndex > -1) {
      selectedOptions.splice(selectedIndex, 1);
    } else {
      if (selectedOptions.length < question.maxSelect) {
        selectedOptions.push(option.text);
      } else {
        showToast(`最多只能选择${question.maxSelect}项`, 'info');
        return;
      }
    }
  } else {
    // 单选，直接保存并下一题
    userAnswers[question.id] = question.id === 'foundation' || question.id === 'programming' || question.id === 'mlKnowledge'
      ? option.value
      : option.text;

    // 显示用户选择
    await showUserMessage(option.text);

    // 下一题
    await delay(800);
    currentQuestionIndex++;

    if (currentQuestionIndex < profileQuestions.length) {
      await showQuestion();
    } else {
      await completeProfile();
    }
  }
}

// 显示用户消息
async function showUserMessage(text) {
  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message user';
  messageEl.innerHTML = `
    <div class="chat-avatar">👤</div>
    <div class="chat-bubble">${text}</div>
  `;
  chatContainer.appendChild(messageEl);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 更新进度条
function updateProgress() {
  const progress = ((currentQuestionIndex + 1) / profileQuestions.length) * 100;
  progressBar.style.width = `${progress}%`;
  progressText.textContent = `${currentQuestionIndex + 1} / ${profileQuestions.length}`;
}

// 完成画像收集
async function completeProfile() {
  // 如果最后是多选题，保存答案
  const lastQuestion = profileQuestions[profileQuestions.length - 1];
  if (lastQuestion.multiSelect && selectedOptions.length > 0) {
    userAnswers[lastQuestion.id] = [...selectedOptions];
  }

  // 保存画像数据
  const profileData = {
    dimensions: {
      foundation: userAnswers.foundation || 3,
      programming: userAnswers.programming || 3,
      mlKnowledge: userAnswers.mlKnowledge || 2,
      learningGoal: userAnswers.learningGoal || '系统学习机器学习',
      timeAvailable: userAnswers.timeAvailable || '每天2-3小时',
      preferredStyle: userAnswers.preferredStyle || '理论与实践结合',
      strongAreas: userAnswers.strongAreas || ['编程开发'],
      weakAreas: userAnswers.weakAreas || ['项目实战']
    },
    completedAt: Date.now()
  };

  Storage.setProfile(profileData);

  // 初始化学习进度
  Storage.setProgress(Storage.getDefaultProgress());
  Storage.setReport(Storage.getDefaultReport());

  // 显示完成消息
  await delay(300);
  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message ai';
  messageEl.innerHTML = `
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble">
      <p>太好了！你的专属学习画像已经生成。根据你的情况，我为你规划了一条个性化的机器学习学习路径。</p>
      <p style="margin-top: 12px;">点击下方按钮，开始你的学习之旅吧！</p>
      <button class="btn btn-primary" style="margin-top: 16px; width: 100%;" onclick="navigateTo('index.html')">
        🚀 前往学习首页
      </button>
    </div>
  `;
  chatContainer.appendChild(messageEl);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}
