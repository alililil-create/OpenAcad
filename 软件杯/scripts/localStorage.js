// localStorage 数据存储模块
const Storage = {
  // 存储键名
  KEYS: {
    USER: 'ml_user',
    PROFILE: 'ml_profile',
    PROGRESS: 'ml_progress',
    REPORT: 'ml_report'
  },

  // 保存用户信息
  setUser(userData) {
    localStorage.setItem(this.KEYS.USER, JSON.stringify(userData));
  },

  // 获取用户信息
  getUser() {
    const data = localStorage.getItem(this.KEYS.USER);
    return data ? JSON.parse(data) : null;
  },

  // 保存用户画像
  setProfile(profileData) {
    localStorage.setItem(this.KEYS.PROFILE, JSON.stringify(profileData));
  },

  // 获取用户画像
  getProfile() {
    const data = localStorage.getItem(this.KEYS.PROFILE);
    return data ? JSON.parse(data) : null;
  },

  // 保存学习进度
  setProgress(progressData) {
    localStorage.setItem(this.KEYS.PROGRESS, JSON.stringify(progressData));
  },

  // 获取学习进度
  getProgress() {
    const data = localStorage.getItem(this.KEYS.PROGRESS);
    return data ? JSON.parse(data) : this.getDefaultProgress();
  },

  // 获取默认学习进度
  getDefaultProgress() {
    return {
      totalKnowledge: 23,
      totalExercises: 156,
      currentPath: ['python-basics', 'data-processing', 'ml-algorithms', 'deep-learning', 'projects'],
      completedPath: ['python-basics', 'data-processing'],
      weekProgress: 65,
      lastStudyDate: Date.now()
    };
  },

  // 保存学习报告
  setReport(reportData) {
    localStorage.setItem(this.KEYS.REPORT, JSON.stringify(reportData));
  },

  // 获取学习报告
  getReport() {
    const data = localStorage.getItem(this.KEYS.REPORT);
    return data ? JSON.parse(data) : this.getDefaultReport();
  },

  // 获取默认学习报告
  getDefaultReport() {
    return {
      strengthPoints: ['数据分析', '特征工程', '模型评估'],
      weakPoints: ['深度学习优化', '神经网络调参'],
      profileChanges: {
        foundation: 3,
        programming: 4,
        mlKnowledge: 3
      },
      reportDate: Date.now()
    };
  },

  // 清除所有数据
  clearAll() {
    Object.values(this.KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  },

  // 检查是否已注册
  isRegistered() {
    return this.getUser() !== null;
  },

  // 检查是否已完成画像收集
  isProfileCompleted() {
    const profile = this.getProfile();
    return profile && profile.completedAt;
  }
};

// 初始化模拟数据（用于演示）
function initMockData() {
  // 如果没有用户数据，创建默认用户
  if (!Storage.getUser()) {
    Storage.setUser({
      username: '学习者',
      registeredAt: Date.now() - 7 * 24 * 60 * 60 * 1000 // 7天前注册
    });
  }

  // 如果没有画像数据，创建默认画像
  if (!Storage.getProfile()) {
    Storage.setProfile({
      dimensions: {
        foundation: 3,
        programming: 4,
        mlKnowledge: 2,
        learningGoal: '系统学习机器学习，找到相关工作',
        timeAvailable: '每天2-3小时',
        preferredStyle: '理论与实践结合',
        strongAreas: ['编程基础', '数学逻辑'],
        weakAreas: ['深度学习', '项目实战']
      },
      completedAt: Date.now() - 6 * 24 * 60 * 60 * 1000
    });
  }
}

// 导出模块
window.Storage = Storage;
window.initMockData = initMockData;
