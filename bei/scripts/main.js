// 公共函数模块

// 显示提示消息
function showToast(message, type = 'info') {
  // 移除已存在的toast
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button onclick="this.parentElement.remove()">×</button>
  `;

  // 添加样式
  toast.style.cssText = `
    position: fixed;
    top: 100px;
    right: 20px;
    padding: 16px 24px;
    background: ${type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#6366F1'};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    z-index: 9999;
    display: flex;
    align-items: center;
    gap: 12px;
    animation: slideIn 0.3s ease;
  `;

  document.body.appendChild(toast);

  // 自动消失
  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }
  }, 3000);
}

// 添加滑入滑出动画
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
`;
document.head.appendChild(styleSheet);

// 导航栏滚动效果
function initNavbarScroll() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });
}

// 格式化日期
function formatDate(timestamp) {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}年${month}月${day}日`;
}

// 格式化相对时间
function formatRelativeTime(timestamp) {
  const now = Date.now();
  const diff = now - timestamp;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  return formatDate(timestamp);
}

// 打字机效果
function typeWriter(element, text, speed = 50) {
  return new Promise((resolve) => {
    let i = 0;
    element.textContent = '';

    function type() {
      if (i < text.length) {
        element.textContent += text.charAt(i);
        i++;
        setTimeout(type, speed);
      } else {
        resolve();
      }
    }

    type();
  });
}

// 延迟函数
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// 获取URL参数
function getUrlParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param);
}

// 页面跳转
function navigateTo(page) {
  window.location.href = page;
}

// 检查登录状态并重定向
function requireAuth(redirectTo = 'register.html') {
  if (!Storage.isRegistered()) {
    navigateTo(redirectTo);
    return false;
  }
  return true;
}

// 初始化页面公共元素
function initCommonPage() {
  initNavbarScroll();
  initMockData();
}

// 导出函数
window.showToast = showToast;
window.initNavbarScroll = initNavbarScroll;
window.formatDate = formatDate;
window.formatRelativeTime = formatRelativeTime;
window.typeWriter = typeWriter;
window.delay = delay;
window.getUrlParam = getUrlParam;
window.navigateTo = navigateTo;
window.requireAuth = requireAuth;
window.initCommonPage = initCommonPage;
