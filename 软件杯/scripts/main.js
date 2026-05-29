function showToast(message, type = 'info') {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button onclick="this.parentElement.remove()">×</button>
  `;

  const bgColor = type === 'success' ? '#6B9E7A' : type === 'error' ? '#D4856B' : '#4A7C8C';
  const textColor = '#FFFFFF';
  const glowColor = type === 'success' ? 'rgba(107, 158, 122, 0.25)' : type === 'error' ? 'rgba(212, 133, 107, 0.25)' : 'rgba(74, 124, 140, 0.25)';

  toast.style.cssText = `
    position: fixed;
    top: 100px;
    right: 20px;
    padding: 16px 24px;
    background: ${bgColor};
    color: ${textColor};
    border-radius: 12px;
    box-shadow: 0 4px 20px ${glowColor}, 0 0 40px ${glowColor};
    backdrop-filter: blur(12px);
    z-index: 9999;
    display: flex;
    align-items: center;
    gap: 12px;
    animation: slideIn 0.3s ease;
    font-weight: 600;
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }
  }, 3000);
}

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

function formatDate(timestamp) {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}年${month}月${day}日`;
}

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

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getUrlParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param);
}

function navigateTo(page) {
  const overlay = document.createElement('div');
  overlay.className = 'page-transition-overlay';
  document.body.appendChild(overlay);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      overlay.classList.add('active');
    });
  });

  setTimeout(() => {
    window.location.href = page;
  }, 400);
}

function initPageEnter() {
  document.body.style.animation = 'pageEnter 0.5s ease-out';
}

function animateNumber(element, target, duration = 1200) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    element.textContent = target;
    return;
  }

  const start = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(target * eased);

    element.textContent = current;

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = target;
    }
  }

  requestAnimationFrame(update);
}

function requireAuth(redirectTo = 'register.html') {
  if (!Storage.isRegistered()) {
    navigateTo(redirectTo);
    return false;
  }
  return true;
}

function initCommonPage() {
  initNavbarScroll();
  initMockData();
  initPageEnter();
  if (typeof initScrollReveal === 'function') {
    initScrollReveal();
  }
}

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
window.initPageEnter = initPageEnter;
window.animateNumber = animateNumber;
