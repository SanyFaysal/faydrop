// API client for Downloader App
const API = {
  baseUrl: '',

  async getSystemStatus() {
    const res = await fetch(`${this.baseUrl}/api/system-status`);
    return await res.json();
  },

  async analyzeLink(url) {
    const res = await fetch(`${this.baseUrl}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    return await res.json();
  },

  async startDownload(params) {
    const res = await fetch(`${this.baseUrl}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return await res.json();
  },

  async getProgress(jobId) {
    const res = await fetch(`${this.baseUrl}/api/progress/${jobId}`);
    return await res.json();
  },

  async cancelJob(jobId) {
    const res = await fetch(`${this.baseUrl}/api/cancel/${jobId}`, {
      method: 'POST'
    });
    return await res.json();
  },

  async getHistory() {
    const res = await fetch(`${this.baseUrl}/api/history`);
    return await res.json();
  },

  async deleteHistoryItem(id, deleteFile = false) {
    const res = await fetch(`${this.baseUrl}/api/history/${id}?delete_file=${deleteFile}`, {
      method: 'DELETE'
    });
    return await res.json();
  },

  async clearHistory() {
    const res = await fetch(`${this.baseUrl}/api/history/clear`, {
      method: 'POST'
    });
    return await res.json();
  },

  async openFolder(path) {
    const res = await fetch(`${this.baseUrl}/api/open-folder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    return await res.json();
  },

  async openFile(path) {
    const res = await fetch(`${this.baseUrl}/api/open-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    return await res.json();
  }
};

