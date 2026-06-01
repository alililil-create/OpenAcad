// API配置（前后端统一端口）
const API_BASE_URL = "";

// 通用请求封装
class MLApiClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
        this.threadId = this.generateThreadId();
    }

    generateThreadId() {
        let tid = localStorage.getItem('ml_thread_id');
        if (!tid) {
            tid = 'thread_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ml_thread_id', tid);
        }
        return tid;
    }

    _getUserId() {
        try {
            const user = JSON.parse(localStorage.getItem('ml_user') || '{}');
            return user.user_id || null;
        } catch {
            return null;
        }
    }

    // 非流式对话
    async chat(message, history = []) {
        const response = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: history.map(msg => ({
                    role: msg.role,
                    content: msg.content
                })),
                thread_id: this.threadId
            })
        });

        const data = await response.json();
        if (!data.success) throw new Error(data.detail || '请求失败');
        return data.data;
    }

    // 流式对话（带Agent状态可视化）
    async chatStream(message, history = {}, onAgentStart, onAgentComplete, onContent, onError, onDone) {
        const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: Array.isArray(history) ? history.map(m => ({ role: m.role, content: m.content })) : [],
                thread_id: this.threadId,
                user_id: this._getUserId()
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

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
                            if (onAgentStart) onAgentStart(data.agent);
                            break;
                        case 'agent_content':
                            if (onContent) onContent(data.agent, data.resource_type, data.preview);
                            break;
                        case 'agent_complete':
                            if (onAgentComplete) onAgentComplete(data.agent, data.status);
                            break;
                        case 'error':
                            if (onError) onError(data.message);
                            break;
                        case 'done':
                            if (onDone) onDone();
                            break;
                    }
                } catch (e) {
                    console.error('SSE解析错误:', e);
                }
            }
        }
    }

    // 用户注册
    async register(username, password, email) {
        const response = await fetch(`${this.baseUrl}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email })
        });
        return response.json();
    }

    // 健康检查
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/api/health`);
        return response.json();
    }

    // 获取视频列表
    async getVideoList(userId) {
        const response = await fetch(`${this.baseUrl}/api/video/list/${userId}`);
        return response.json();
    }

    // 获取用户画像
    async getProfile(userId) {
        const response = await fetch(`${this.baseUrl}/api/profile/${userId}`);
        return response.json();
    }

    // 删除视频记录
    async deleteVideo(resourceId) {
        const response = await fetch(`${this.baseUrl}/api/video/${resourceId}`, {
            method: 'DELETE'
        });
        return response.json();
    }

    // 视频生成（SSE 流式）
    async generateVideo(params, onStatus, onDone, onError) {
        const response = await fetch(`${this.baseUrl}/api/video/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.startsWith('data: '));

            for (const line of lines) {
                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.type === 'status' && onStatus) {
                        onStatus(data);
                    } else if (data.type === 'done' && onDone) {
                        onDone(data);
                    } else if (data.type === 'error' && onError) {
                        onError(data.message);
                    }
                } catch (e) {
                    console.error('视频SSE解析错误:', e);
                }
            }
        }
    }
}

// 全局实例
const apiClient = new MLApiClient();

// 导出
window.MLApiClient = MLApiClient;
window.apiClient = apiClient;
