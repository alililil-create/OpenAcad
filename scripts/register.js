// 登录/注册页逻辑 - 接入后端 API

// 密码显示/隐藏切换
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁️';
  }
}

// 当前模式：login 或 register
let currentMode = 'login';

// 切换登录/注册模式
function switchTab(mode) {
  currentMode = mode;
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const authHeader = document.getElementById('authHeader');
  const confirmGroup = document.getElementById('confirmGroup');
  const submitBtn = document.getElementById('submitBtn');
  const authFooter = document.getElementById('authFooter');

  if (mode === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    authHeader.innerHTML = '<h1>欢迎回来</h1><p>登录你的账号，继续学习之旅</p>';
    confirmGroup.style.display = 'none';
    submitBtn.textContent = '登录';
    authFooter.innerHTML = '<p>还没有账号？<a href="#" onclick="switchTab(\'register\')">立即注册</a></p>';
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    authHeader.innerHTML = '<h1>欢迎加入</h1><p>创建账号，开始你的机器学习之旅</p>';
    confirmGroup.style.display = '';
    submitBtn.textContent = '注册并开始';
    authFooter.innerHTML = '<p>已有账号？<a href="#" onclick="switchTab(\'login\')">立即登录</a></p>';
  }

  // 清除错误提示
  document.querySelectorAll('.form-error').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.form-input').forEach(el => el.style.borderColor = '');
}

document.addEventListener('DOMContentLoaded', () => {
  const registerForm = document.getElementById('registerForm');
  const usernameInput = document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const usernameError = document.getElementById('usernameError');
  const passwordError = document.getElementById('passwordError');
  const confirmPasswordError = document.getElementById('confirmPasswordError');

  // 初始化：清除旧数据，检查登录状态
  checkAndRedirectIfLoggedIn();

  function checkAndRedirectIfLoggedIn() {
    var savedUser = Storage.getUser();
    if (savedUser && savedUser.token && savedUser.user_id) {
      navigateTo('index.html');
    }
  }

  function validateUsername() {
    const username = usernameInput.value.trim();
    if (!username) { showError(usernameError, '请输入账号'); return false; }
    if (username.length < 2) { showError(usernameError, '账号至少2个字符'); return false; }
    hideError(usernameError);
    return true;
  }

  function validatePassword() {
    const password = passwordInput.value;
    if (!password) { showError(passwordError, '请输入密码'); return false; }
    if (password.length < 4) { showError(passwordError, '密码至少4个字符'); return false; }
    hideError(passwordError);
    return true;
  }

  function validateConfirmPassword() {
    if (currentMode === 'login') return true;
    const confirmPassword = confirmPasswordInput.value;
    if (!confirmPassword) { showError(confirmPasswordError, '请确认密码'); return false; }
    if (confirmPassword !== passwordInput.value) { showError(confirmPasswordError, '两次密码不一致'); return false; }
    hideError(confirmPasswordError);
    return true;
  }

  function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    if (element.previousElementSibling) element.previousElementSibling.style.borderColor = '#EF4444';
  }

  function hideError(element) {
    element.style.display = 'none';
    if (element.previousElementSibling) element.previousElementSibling.style.borderColor = '#D1D5DB';
  }

  [usernameInput, passwordInput, confirmPasswordInput].forEach(input => {
    input.addEventListener('focus', () => {
      const errorEl = document.getElementById(input.id + 'Error');
      if (errorEl) hideError(errorEl);
    });
  });

  // 表单提交
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const isUsernameValid = validateUsername();
    const isPasswordValid = validatePassword();
    const isConfirmValid = validateConfirmPassword();

    if (!isUsernameValid || !isPasswordValid || !isConfirmValid) return;

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    const originalText = submitBtn.textContent;
    submitBtn.textContent = currentMode === 'login' ? '登录中...' : '注册中...';

    try {
      const endpoint = currentMode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: usernameInput.value.trim(),
          password: passwordInput.value
        })
      });

      const result = await response.json();

      if (result.success) {
        // 先清除所有旧数据，再写入新数据
        Storage.clearAll();

        Storage.setUser({
          user_id: result.data.user_id,
          username: result.data.username,
          token: result.data.token,
          hasProfile: result.data.has_profile || false
        });

        if (currentMode === 'login') {
          showToast('登录成功！', 'success');
        } else {
          showToast('注册成功！', 'success');
        }

        setTimeout(() => {
          if (result.data.has_profile) {
            navigateTo('index.html');
          } else {
            navigateTo('wizard.html');
          }
        }, 800);

      } else {
        showToast(result.message || result.detail || '操作失败，请重试', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }

    } catch (err) {
      console.error('请求失败:', err);
      showToast('服务器连接失败，请确保后端已启动', 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });
});