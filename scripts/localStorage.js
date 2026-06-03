// localStorage 数据存储模块
const Storage = {
  KEYS: {
    USER: 'ml_user',
    PROFILE: 'ml_profile',
    PROGRESS: 'ml_progress',
    REPORT: 'ml_report',
    CURRENT_USER_ID: 'ml_current_user_id',
    PROFILE_CACHE: 'ml_profile_cache',
    API_BASE_URL: 'ml_api_base_url',
    WIZARD_DATA: 'ml_wizard_data',
  },

  ALL_KEYS: function() {
    return Object.values(this.KEYS);
  },

  setUser(userData) {
    localStorage.setItem(this.KEYS.USER, JSON.stringify(userData));
    if (userData && userData.user_id) {
      localStorage.setItem(this.KEYS.CURRENT_USER_ID, String(userData.user_id));
    }
  },

  getUser() {
    const data = localStorage.getItem(this.KEYS.USER);
    return data ? JSON.parse(data) : null;
  },

  getUserID() {
    var raw = localStorage.getItem(this.KEYS.CURRENT_USER_ID);
    if (raw) return parseInt(raw);
    var user = this.getUser();
    if (user && user.user_id) {
      localStorage.setItem(this.KEYS.CURRENT_USER_ID, String(user.user_id));
      return user.user_id;
    }
    return 0;
  },

  setProfile(profileData) {
    localStorage.setItem(this.KEYS.PROFILE, JSON.stringify(profileData));
  },

  getProfile() {
    const data = localStorage.getItem(this.KEYS.PROFILE);
    return data ? JSON.parse(data) : null;
  },

  setProgress(progressData) {
    localStorage.setItem(this.KEYS.PROGRESS, JSON.stringify(progressData));
  },

  getProgress() {
    const data = localStorage.getItem(this.KEYS.PROGRESS);
    return data ? JSON.parse(data) : null;
  },

  setReport(reportData) {
    localStorage.setItem(this.KEYS.REPORT, JSON.stringify(reportData));
  },

  getReport() {
    const data = localStorage.getItem(this.KEYS.REPORT);
    return data ? JSON.parse(data) : null;
  },

  clearAll() {
    this.ALL_KEYS().forEach(function(key) {
      localStorage.removeItem(key);
    });
  },

  isRegistered() {
    var user = this.getUser();
    return user && user.user_id && user.token;
  },

  isProfileCompleted() {
    const profile = this.getProfile();
    return profile && profile.completedAt;
  }
};

window.Storage = Storage;