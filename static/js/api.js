// API client for Faydrop App • By Faysal
const API = {
  baseUrl: '',

  getDeviceId() {
    let id = localStorage.getItem('faydrop_device_id');
    if (!id) {
      id = 'dev_' + Math.random().toString(36).substring(2, 8) + '_' + Date.now().toString(36);
      localStorage.setItem('faydrop_device_id', id);
    }
    return id;
  },

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-Device-Id': this.getDeviceId()
    };
  },

  async getSystemStatus() {
    const res = await fetch(`${this.baseUrl}/api/system-status`);
    return await res.json();
  },

  async analyzeLink(url) {
    const res = await fetch(`${this.baseUrl}/api/analyze`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ url, device_id: this.getDeviceId() })
    });
    return await res.json();
  },

  async startDownload(params) {
    params.device_id = this.getDeviceId();
    const res = await fetch(`${this.baseUrl}/api/download`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(params)
    });
    return await res.json();
  },

  async getProgress(jobId) {
    const res = await fetch(`${this.baseUrl}/api/progress/${jobId}`, {
      headers: this.getHeaders()
    });
    return await res.json();
  },

  async cancelJob(jobId) {
    const res = await fetch(`${this.baseUrl}/api/cancel/${jobId}`, {
      method: 'POST',
      headers: this.getHeaders()
    });
    return await res.json();
  },

  async getHistory() {
    const res = await fetch(`${this.baseUrl}/api/history?device_id=${encodeURIComponent(this.getDeviceId())}`, {
      headers: this.getHeaders()
    });
    return await res.json();
  },

  async deleteHistoryItem(id, deleteFile = false) {
    const res = await fetch(`${this.baseUrl}/api/history/${id}?device_id=${encodeURIComponent(this.getDeviceId())}&delete_file=${deleteFile}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    });
    return await res.json();
  },

  async clearHistory() {
    const res = await fetch(`${this.baseUrl}/api/history/clear?device_id=${encodeURIComponent(this.getDeviceId())}`, {
      method: 'POST',
      headers: this.getHeaders()
    });
    return await res.json();
  },

  async openFolder(path) {
    const res = await fetch(`${this.baseUrl}/api/open-folder`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ path })
    });
    return await res.json();
  },

  async openFile(path) {
    const res = await fetch(`${this.baseUrl}/api/open-file`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ path })
    });
    return await res.json();
  },

  async getSettings() {
    const res = await fetch(`${this.baseUrl}/api/settings`);
    return await res.json();
  },

  async saveSettings(settings) {
    const res = await fetch(`${this.baseUrl}/api/settings`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(settings)
    });
    return await res.json();
  }
};
