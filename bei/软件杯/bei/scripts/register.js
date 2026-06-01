// 注册页逻辑

document.addEventListener('DOMContentLoaded', () => {
  const registerForm = document.getElementById('registerForm');
  const usernameInput = document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const usernameError = document.getElementById('usernameError');
  const passwordError = document.getElementById('passwordError');
  const confirmPasswordError = document.getElementById('confirmPasswordError');

  // 初始化：如果已注册且已完成画像，跳转到首页
  if (Storage.isRegistered() && Storage.isProfileCompleted()) {
    navigateTo('index.html');
    return;
  }

  // 如果已注册但未完成画像，跳转到画像页
  if (Storage.isRegistered() && !Storage.isProfileCompleted()) {
    navigateTo('profile.html');
    return;
  }

  // 表单验证
  function validateUsername() {
    const username = usernameInput.value.trim();
    if (!username) {
      showError(usernameError, '请输入账号');
      return false;
    }
    if (username.length < 3) {
      showError(usernameError, '账号至少3个字符');
      return false;
    }
    hideError(usernameError);
    return true;
  }

  function validatePassword() {
    const password = passwordInput.value;
    if (!password) {
      showError(passwordError, '请输入密码');
      return false;
    }
    if (password.length < 6) {
      showError(passwordError, '密码至少6个字符');
      return false;
    }
    hideError(passwordError);
    return true;
  }

  function validateConfirmPassword() {
    const confirmPassword = confirmPasswordInput.value;
    if (!confirmPassword) {
      showError(confirmPasswordError, '请确认密码');
      return false;
    }
    if (confirmPassword !== passwordInput.value) {
      showError(confirmPasswordError, '两次密码不一致');
      return false;
    }
    hideError(confirmPasswordError);
    return true;
  }

  function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    element.previousElementSibling.style.borderColor = '#EF4444';
  }

  function hideError(element) {
    element.style.display = 'none';
    element.previousElementSibling.style.borderColor = '#E2E8F0';
  }

  // 输入框获取焦点时移除错误状态
  [usernameInput, passwordInput, confirmPasswordInput].forEach(input => {
    input.addEventListener('focus', () => {
      const errorEl = document.getElementById(input.id + 'Error');
      if (errorEl) hideError(errorEl);
    });
  });

  // 表单提交
  registerForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const isUsernameValid = validateUsername();
    const isPasswordValid = validatePassword();
    const isConfirmValid = validateConfirmPassword();

    if (isUsernameValid && isPasswordValid && isConfirmValid) {
      // 保存用户信息
      Storage.setUser({
        username: usernameInput.value.trim(),
        registeredAt: Date.now()
      });

      showToast('注册成功！即将跳转到画像收集页面...', 'success');

      // 跳转到画像收集页
      setTimeout(() => {
        navigateTo('profile.html');
      }, 1500);
    }
  });
});
