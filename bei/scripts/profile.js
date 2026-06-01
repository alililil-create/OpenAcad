// AI画像分析页逻辑 - 基于已有画像触发多智能体链路

let chatHistory = [];
let isProcessing = false;

document.addEventListener('DOMContentLoaded', async () => {
  const chatContainer = document.getElementById('chatContainer');

  // 显示引导说明
  showGuideMessage();
});

function showGuideMessage() {
  const chatContainer = document.getElementById('chatContainer');

  chatContainer.innerHTML = `
    <div class="chat-message ai">
      <div class="chat-avatar">🤖</div>
      <div class="chat-bubble">
        <p>欢迎使用 AI 智能画像分析 🎓</p>
        <p style="margin-top: 12px;">系统将读取你的学习画像，8个 AI Agent 依次协作：</p>
        <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">🎯 <strong>意图识别</strong> - 分析学习需求</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">👤 <strong>画像Agent</strong> - 深度分析能力</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">📝 <strong>文档Agent</strong> - 生成教学材料</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">❓ <strong>题库Agent</strong> - 定制练习题目</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">🗺️ <strong>导图Agent</strong> - 构建知识框架</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">💻 <strong>代码Agent</strong> - 提供实践案例</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">🛤️ <strong>路径Agent</strong> - 规划学习路线</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">🎥 <strong>视频Agent</strong> - 生成教学视频</div>
          <div style="background:#f8f9fa;padding:8px 12px;border-radius:8px;">✅ <strong>总结节点</strong> - 整合所有产出</div>
        </div>
        <p style="margin-top: 16px; color: #666;">👆 点击上方「<strong>开始智能分析</strong>」按钮启动</p>
      </div>
    </div>
  `;
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function triggerProfileAnalysis() {
  if (isProcessing) return;

  // 获取用户ID
  let userId = null;
  try {
    const user = JSON.parse(localStorage.getItem('ml_user') || 'null');
    userId = user?.user_id;
  } catch(e) {}

  if (!userId) {
    appendAIMessage('⚠️ 请先登录后再使用此功能。<a href="register.html">去登录</a>');
    return;
  }

  isProcessing = true;

  // 隐藏启动按钮
  document.getElementById('startSection').style.display = 'none';

  // 重置所有 Agent 状态
  resetAllAgentStatus();

  updateProgress(10, '正在读取学习画像...');

  // 清空并显示过程
  const chatContainer = document.getElementById('chatContainer');
  chatContainer.innerHTML = `
    <div class="chat-message ai">
      <div class="chat-avatar">🤖</div>
      <div class="chat-bubble">
        <p>📊 正在读取你的学习画像数据...</p>
        <p style="font-size:12px;color:#888;">User ID: ${userId}</p>
      </div>
    </div>
  `;

  updateProgress(20, '调用 AI 智能体...');

  try {
    await callProfileAnalyzeAPI(userId);
  } catch (error) {
    console.error('分析失败:', error);
    updateProgress(0, '分析失败');
    appendAIMessage(`❌ 分析失败：${error.message}`);
    document.getElementById('startSection').style.display = 'block';
  } finally {
    isProcessing = false;
  }
}

async function callProfileAnalyzeAPI(userId) {
  const response = await fetch(`/api/profile/analyze/${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(err.detail || `请求失败 (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let agentCount = 0;
  const agentResults = {};
  const totalAgents = 9;

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
            agentCount++;
            updateAgentStatusUI(data.agent, 'working');
            updateWorkflowStep(data.agent);
            updateProgress(20 + Math.round(agentCount / totalAgents * 70), getAgentDisplayName(data.agent) + ' 工作中...');

            appendToAIAnalysis(`🚀 <strong>${getAgentDisplayName(data.agent)}</strong> 正在分析...`);
            break;

          case 'agent_content':
            agentResults[data.agent] = { type: data.resource_type, preview: data.preview };
            if (data.resource_type === 'profile') {
              appendToAIAnalysis(`✅ ${data.preview}`);
            } else if (data.resource_type === 'document') {
              appendToAIAnalysis(`📄 教学文档已生成`);
            } else if (data.resource_type === 'questions') {
              appendToAIAnalysis(`✏️ 练习题已生成`);
            } else if (data.resource_type === 'mindmap') {
              appendToAIAnalysis(`🗺️ 知识导图已生成`);
            } else if (data.resource_type === 'code_examples') {
              appendToAIAnalysis(`💻 代码案例已生成`);
            } else if (data.resource_type === 'video') {
              const videoUrl = data.video_url || '';
              const videoHtml = videoUrl
                ? `<br><video src="${videoUrl}" controls style="max-width:100%;max-height:300px;margin-top:8px;border-radius:8px;"></video>`
                : '';
              appendToAIAnalysis(`🎥 ${data.preview}${videoHtml}`);
            }
            break;

          case 'agent_complete':
            updateAgentStatusUI(data.agent, 'completed');
            break;

          case 'error':
            appendToAIAnalysis(`⚠️ 错误：${data.message}`);
            break;

          case 'done':
            updateProgress(100, '分析完成！');
            updateAllAgentsCompleted();
            appendToAIAnalysis('✨ 所有 Agent 协作完成！你的个性化学习资源已生成。');

            setTimeout(() => showCompletionActions(), 1500);
            break;
        }
      } catch (e) {
        console.error('SSE解析错误:', e);
      }
    }
  }
}

function appendToAIAnalysis(text) {
  const chatContainer = document.getElementById('chatContainer');
  const bubbles = chatContainer.querySelectorAll('.chat-bubble');
  const lastBubble = bubbles[bubbles.length - 1];

  if (lastBubble) {
    const textEl = document.createElement('p');
    textEl.style.cssText = 'margin: 3px 0; font-size: 14px;';
    textEl.innerHTML = text;
    lastBubble.appendChild(textEl);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
}

function updateAgentStatusUI(agentName, status) {
  const cardId = 'card-' + agentName;
  const card = document.getElementById(cardId);

  if (!card) {
    console.warn('找不到Agent卡片:', cardId);
    return;
  }

  const statusEl = card.querySelector('.status');
  if (statusEl) {
    statusEl.className = 'status ' + status;
    statusEl.textContent = {
      'idle': '待命中',
      'working': '工作中...',
      'completed': '已完成',
      'error': '出错'
    }[status] || status;
  }
}

function resetAllAgentStatus() {
  const cards = document.querySelectorAll('.agent-card');
  cards.forEach(card => {
    const statusEl = card.querySelector('.status');
    if (statusEl) {
      statusEl.className = 'status idle';
      statusEl.textContent = '待命中';
    }
  });

  // 重置流程步骤
  for (let i = 1; i <= 5; i++) {
    const stepEl = document.getElementById(`step-${i}`);
    if (stepEl) {
      stepEl.classList.remove('active');
    }
  }
  document.getElementById('step-1')?.classList.add('active');
}

function updateAllAgentsCompleted() {
  const cards = document.querySelectorAll('.agent-card');
  cards.forEach(card => {
    const statusEl = card.querySelector('.status');
    if (statusEl && statusEl.classList.contains('idle')) {
      statusEl.className = 'status completed';
      statusEl.textContent = '已完成';
    }
  });
}

function getAgentDisplayName(agentKey) {
  const names = {
    'analyze_intent': '意图识别',
    'build_profile': '画像Agent',
    'generate_doc': '文档Agent',
    'generate_questions': '题库Agent',
    'generate_mindmap': '导图Agent',
    'generate_code': '代码Agent',
    'plan_path': '路径Agent',
    'generate_video': '视频Agent',
    'final_summary': '总结节点'
  };
  return names[agentKey] || agentKey;
}

function updateWorkflowStep(agentName) {
  const stepMap = {
    'analyze_intent': '2',
    'build_profile': '2',
    'generate_doc': '3',
    'generate_questions': '3',
    'generate_mindmap': '3',
    'generate_code': '3',
    'plan_path': '4',
    'generate_video': '4',
    'final_summary': '5'
  };

  const stepNum = stepMap[agentName];
  if (stepNum) {
    for (let i = 1; i <= 5; i++) {
      const stepEl = document.getElementById(`step-${i}`);
      if (stepEl) {
        if (i <= parseInt(stepNum)) {
          stepEl.classList.add('active');
        } else {
          stepEl.classList.remove('active');
        }
      }
    }
  }
}

function updateProgress(percent, text) {
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');

  if (progressFill) progressFill.style.width = percent + '%';
  if (progressText) progressText.textContent = text;
}

function showCompletionActions() {
  const chatContainer = document.getElementById('chatContainer');

  const completeDiv = document.createElement('div');
  completeDiv.className = 'chat-message ai';
  completeDiv.innerHTML = `
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble">
      <p>所有分析已完成！✨</p>
      <p style="margin-top: 12px;">根据你的学习画像，7个 AI Agent 为你生成了个性化的学习资源。</p>
      <button onclick="navigateTo('index.html')"
              class="btn btn-primary"
              style="margin-top: 16px; width: 100%; padding: 14px; font-size: 16px;">
        🚀 前往学习首页查看完整方案
      </button>
    </div>
  `;
  chatContainer.appendChild(completeDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendAIMessage(text) {
  const chatContainer = document.getElementById('chatContainer');

  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message ai';
  messageEl.innerHTML = `
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble">
      <p>${text}</p>
    </div>
  `;
  chatContainer.appendChild(messageEl);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}