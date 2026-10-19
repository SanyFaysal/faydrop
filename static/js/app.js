// OmniStream Application Logic • Developed by Faysal
document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    analyzedMedia: null,
    selectedType: 'video', // 'video' | 'audio'
    selectedResolution: '1080p',
    selectedVideoFormat: null,
    selectedContainer: 'mp4',
    selectedAudioPreset: 'mp3-320',
    activeJobs: new Map(),
    settings: null,
    eventSources: new Map(),
    historyItems: [],
    historyFilter: 'all', // 'all' | 'video' | 'audio'
    historySearchQuery: ''
  };

  // DOM Elements
  const urlInput = document.getElementById('url-input');
  const btnClearUrl = document.getElementById('btn-clear-url');
  const btnPasteClipboard = document.getElementById('btn-paste-clipboard');
  const btnAnalyze = document.getElementById('btn-analyze');
  const analyzeBtnText = document.getElementById('analyze-btn-text');
  const analyzeSpinner = document.getElementById('analyze-spinner');
  const platformIcon = document.getElementById('platform-icon');

  const errorBanner = document.getElementById('error-banner');
  const errorMessage = document.getElementById('error-message');
  const errorHint = document.getElementById('error-hint');
  const btnCloseError = document.getElementById('btn-close-error');

  const mediaCard = document.getElementById('media-card');
  const mediaThumbnail = document.getElementById('media-thumbnail');
  const mediaFallbackIcon = document.getElementById('media-fallback-icon');
  const mediaMainIcon = document.getElementById('media-main-icon');
  const mediaDuration = document.getElementById('media-duration');
  const mediaPlatformBadge = document.getElementById('media-platform-badge');
  const mediaPlatformIcon = document.getElementById('media-platform-icon');
  const mediaPlatformName = document.getElementById('media-platform-name');
  const mediaTitle = document.getElementById('media-title');
  const mediaUploader = document.getElementById('media-uploader');
  const mediaViews = document.getElementById('media-views');
  const mediaViewsContainer = document.getElementById('media-views-container');
  const mediaExternalLink = document.getElementById('media-external-link');

  const tabVideo = document.getElementById('tab-video');
  const tabAudio = document.getElementById('tab-audio');
  const panelVideo = document.getElementById('panel-video');
  const panelAudio = document.getElementById('panel-audio');
  const videoFormatsGrid = document.getElementById('video-formats-grid');
  const audioFormatsGrid = document.getElementById('audio-formats-grid');
  const btnExtMp4 = document.getElementById('btn-ext-mp4');
  const btnExtMkv = document.getElementById('btn-ext-mkv');

  const btnToggleFilename = document.getElementById('btn-toggle-filename');
  const customFilenameBox = document.getElementById('custom-filename-box');
  const customFilenameInput = document.getElementById('custom-filename-input');
  const btnStartDownload = document.getElementById('btn-start-download');
  const downloadButtonLabel = document.getElementById('download-button-label');

  const activeDownloadsList = document.getElementById('active-downloads-list');
  const activeCountBadge = document.getElementById('active-count-badge');
  const historyList = document.getElementById('history-list');
  const historyCountBadge = document.getElementById('history-count-badge');
  const btnRefreshHistory = document.getElementById('btn-refresh-history');
  const btnClearHistory = document.getElementById('btn-clear-history');
  const historySearchInput = document.getElementById('history-search-input');
  const filterAll = document.getElementById('filter-all');
  const filterVideo = document.getElementById('filter-video');
  const filterAudio = document.getElementById('filter-audio');

  const btnOpenDownloadDir = document.getElementById('btn-open-download-dir');
  const btnOpenSettings = document.getElementById('btn-open-settings');
  const btnCloseSettings = document.getElementById('btn-close-settings');
  const btnCancelSettings = document.getElementById('btn-cancel-settings');
  const btnSaveSettings = document.getElementById('btn-save-settings');
  const settingsModal = document.getElementById('settings-modal');
  const settingsDownloadDir = document.getElementById('settings-download-dir');
  const btnSettingsOpenDir = document.getElementById('btn-settings-open-dir');
  const settingsBrowserCookies = document.getElementById('settings-browser-cookies');
  const settingsEmbedMetadata = document.getElementById('settings-embed-metadata');
  const settingsEmbedThumbnail = document.getElementById('settings-embed-thumbnail');
  const statusText = document.getElementById('status-text');

  // --- Initial System & Settings Setup ---
  async function init() {
    try {
      const status = await API.getSystemStatus();
      if (status) {
        if (statusText) statusText.textContent = `Engine Ready • FFmpeg 7.1`;
        const diagYt = document.getElementById('diag-ytdlp');
        const diagFf = document.getElementById('diag-ffmpeg');
        const diagNode = document.getElementById('diag-node');
        if (diagYt) diagYt.textContent = status.ytdlp_version;
        if (diagFf) diagFf.textContent = status.ffmpeg_available ? 'Active (7.1)' : 'Not Found';
        if (diagNode) diagNode.textContent = status.node_available ? 'Node.js Active' : 'Fallback';
      }
    } catch (e) {
      console.warn("Status check failed:", e);
    }

    try {
      state.settings = await API.getSettings();
      if (state.settings && state.settings.download_dir) {
        settingsDownloadDir.value = state.settings.download_dir;
        settingsBrowserCookies.value = state.settings.browser_cookies || 'none';
        settingsEmbedMetadata.checked = state.settings.embed_metadata !== false;
        settingsEmbedThumbnail.checked = state.settings.embed_thumbnail !== false;
      }
    } catch (e) {
      console.warn("Settings load failed:", e);
    }

    loadHistory();
    setupEventListeners();
    startJobPolling();
  }

  // --- URL Detection & Helper Functions ---
  function detectPlatform(url) {
    const val = (url || '').toLowerCase().trim();
    if (val.includes('youtube.com') || val.includes('youtu.be')) {
      return { name: 'YouTube', icon: 'youtube', color: '#EF4444' };
    } else if (val.includes('facebook.com') || val.includes('fb.watch') || val.includes('fb.com')) {
      return { name: 'Facebook', icon: 'facebook', color: '#3B82F6' };
    } else if (val.includes('instagram.com')) {
      return { name: 'Instagram', icon: 'instagram', color: '#EC4899' };
    } else if (val.includes('tiktok.com')) {
      return { name: 'TikTok', icon: 'music-2', color: '#06B6D4' };
    } else if (val.includes('twitter.com') || val.includes('x.com')) {
      return { name: 'Twitter/X', icon: 'twitter', color: '#38BDF8' };
    } else if (val.includes('soundcloud.com')) {
      return { name: 'SoundCloud', icon: 'headphones', color: '#F97316' };
    }
    return { name: 'Web Media', icon: 'globe', color: '#8B5CF6' };
  }

  function updateInputIcon() {
    const url = urlInput.value.trim();
    if (!url) {
      btnClearUrl.classList.add('hidden');
      if (platformIcon) {
        platformIcon.setAttribute('data-lucide', 'link');
        platformIcon.style.color = '#8B5CF6';
      }
    } else {
      btnClearUrl.classList.remove('hidden');
      const p = detectPlatform(url);
      if (platformIcon) {
        platformIcon.setAttribute('data-lucide', p.icon);
        platformIcon.style.color = p.color;
      }
    }
    lucide.createIcons();
  }

  // --- Robust Thumbnail Element Generator with Vector Fallback ---
  function renderThumbnailHtml(thumbnailUrl, platform, format, isAudio, sizeClass = 'w-12 h-12') {
    const p = platform || { icon: 'video', color: '#8B5CF6' };
    const iconName = isAudio ? 'music' : (p.icon || 'video');
    const formatBadge = format ? format.toUpperCase() : (isAudio ? 'MP3' : 'MP4');
    const brandColor = p.color || '#8B5CF6';

    // If no thumbnail URL is provided, display clean vector icon
    if (!thumbnailUrl) {
      return `
        <div class="${sizeClass} rounded-xl thumbnail-box border border-white/10 shrink-0 shadow-md">
          <div class="flex items-center justify-center w-full h-full" style="color: ${brandColor};">
            <i data-lucide="${iconName}" class="w-5 h-5"></i>
          </div>
          <span class="absolute bottom-1 right-1 text-[8px] px-1 py-0.2 rounded bg-black/85 font-mono text-white font-bold tracking-tight shadow border border-white/10">${formatBadge}</span>
        </div>
      `;
    }

    // With image and automatic graceful fallback on error
    return `
      <div class="${sizeClass} rounded-xl thumbnail-box border border-white/10 shrink-0 shadow-md">
        <!-- Fallback vector icon (always rendered underneath) -->
        <div class="thumbnail-fallback flex items-center justify-center w-full h-full" style="color: ${brandColor};">
          <i data-lucide="${iconName}" class="w-5 h-5"></i>
        </div>
        <!-- Main Image with no-referrer & instant fallback -->
        <img 
          src="${thumbnailUrl}" 
          referrerpolicy="no-referrer"
          loading="lazy"
          class="thumbnail-img absolute inset-0 w-full h-full object-cover transition-opacity duration-300"
          onload="this.style.opacity='1';"
          onerror="this.remove();"
          style="opacity: 0;"
        >
        <span class="absolute bottom-1 right-1 text-[8px] px-1 py-0.2 rounded bg-black/85 font-mono text-white font-bold tracking-tight shadow border border-white/10 z-10">${formatBadge}</span>
      </div>
    `;
  }

  // --- Toast Notifications ---
  function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconName = 'info';
    if (type === 'success') iconName = 'check-circle';
    if (type === 'error') iconName = 'alert-triangle';

    toast.innerHTML = `
      <i data-lucide="${iconName}" class="w-4 h-4 shrink-0"></i>
      <span class="text-xs font-semibold flex-1 leading-snug">${message}</span>
      <button class="toast-close p-1 hover:text-white text-slate-300">
        <i data-lucide="x" class="w-3.5 h-3.5"></i>
      </button>
    `;

    container.appendChild(toast);
    lucide.createIcons();

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => toast.remove());

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(15px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  }

  // --- Analyze URL Handler ---
  async function handleAnalyze() {
    const url = urlInput.value.trim();
    if (!url) {
      showError("Please paste or type a valid video link first.");
      urlInput.focus();
      return;
    }

    hideError();

    btnAnalyze.disabled = true;
    analyzeBtnText.classList.add('hidden');
    analyzeSpinner.classList.remove('hidden');

    try {
      const res = await API.analyzeLink(url);
      if (!res.success) {
        showError(res.error || "Unable to retrieve video information. Please verify the URL.");
        mediaCard.classList.add('hidden');
      } else {
        state.analyzedMedia = res.data;
        renderMediaCard(res.data);
        showToast("Link analyzed! Pick your format and click download.", "success");
      }
    } catch (err) {
      showError("Failed to communicate with downloader engine: " + err.message);
    } finally {
      btnAnalyze.disabled = false;
      analyzeBtnText.classList.remove('hidden');
      analyzeSpinner.classList.add('hidden');
    }
  }

  function showError(msg, hint = "") {
    errorBanner.classList.remove('hidden');
    errorMessage.textContent = msg;
    errorHint.textContent = hint || "Tip: Verify that the link is public and accessible in your web browser.";
    lucide.createIcons();
  }

  function hideError() {
    errorBanner.classList.add('hidden');
  }

  // --- Render Media Card & Formats ---
  function renderMediaCard(data) {
    mediaCard.classList.remove('hidden');

    // Thumbnail Preview with Fallback Handler
    const platform = data.platform || detectPlatform(data.url);
    if (data.thumbnail) {
      mediaThumbnail.src = data.thumbnail;
      mediaThumbnail.style.display = 'block';
      mediaThumbnail.onerror = () => {
        mediaThumbnail.style.display = 'none';
        mediaFallbackIcon.classList.remove('hidden');
      };
      mediaThumbnail.onload = () => {
        mediaThumbnail.style.display = 'block';
        mediaFallbackIcon.classList.add('hidden');
      };
    } else {
      mediaThumbnail.style.display = 'none';
      mediaFallbackIcon.classList.remove('hidden');
    }

    mediaMainIcon.setAttribute('data-lucide', platform.icon || 'video');
    mediaTitle.textContent = data.title;
    mediaUploader.textContent = data.uploader || 'Creator';
    mediaDuration.textContent = data.duration_str || '--:--';

    if (data.view_count_str) {
      mediaViewsContainer.classList.remove('hidden');
      mediaViews.textContent = `${data.view_count_str} views`;
    } else {
      mediaViewsContainer.classList.add('hidden');
    }

    mediaExternalLink.href = data.url;

    // Platform Badge
    mediaPlatformName.textContent = platform.name;
    mediaPlatformIcon.setAttribute('data-lucide', platform.icon || 'video');
    mediaPlatformBadge.style.backgroundColor = `${platform.color || '#8B5CF6'}20`;
    mediaPlatformBadge.style.color = platform.color || '#A78BFA';
    mediaPlatformBadge.style.borderColor = `${platform.color || '#8B5CF6'}40`;

    // Render Video Formats
    renderVideoFormats(data.video_formats || []);

    // Render Audio Formats
    renderAudioFormats(data.audio_formats || []);

    // Update CTA button label
    updateDownloadButtonLabel();

    lucide.createIcons();

    mediaCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderVideoFormats(formats) {
    videoFormatsGrid.innerHTML = '';
    if (!formats || formats.length === 0) {
      videoFormatsGrid.innerHTML = `<div class="col-span-full text-xs text-slate-400 p-2 text-center">Standard video stream will be downloaded.</div>`;
      return;
    }

    let defaultFormat = formats.find(f => f.resolution === '1080p') || formats[0];
    state.selectedResolution = defaultFormat.resolution;
    state.selectedVideoFormat = defaultFormat;

    formats.forEach(f => {
      const card = document.createElement('div');
      const isSelected = f.resolution === defaultFormat.resolution;
      card.className = `format-card ${isSelected ? 'selected' : ''}`;
      card.dataset.resolution = f.resolution;

      let badgeHtml = '';
      if (f.badge) {
        let badgeColor = 'bg-slate-800 text-slate-300';
        if (f.height >= 2160) badgeColor = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
        else if (f.height >= 1440) badgeColor = 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
        else if (f.height >= 1080) badgeColor = 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30';
        else if (f.height >= 720) badgeColor = 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
        badgeHtml = `<span class="text-[9px] px-1.5 py-0.2 rounded font-bold ${badgeColor}">${f.badge}</span>`;
      }

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-extrabold text-sm text-white">${f.resolution}</span>
          ${badgeHtml}
        </div>
        <div class="mt-1 flex items-center justify-between text-[10px] text-slate-400">
          <span>${f.fps > 30 ? f.fps + ' fps' : 'Standard'}</span>
          <span class="font-mono text-purple-300 font-medium">${f.filesize_str || 'Adaptive'}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('#video-formats-grid .format-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        state.selectedResolution = f.resolution;
        state.selectedVideoFormat = f;
        updateDownloadButtonLabel();
      });

      videoFormatsGrid.appendChild(card);
    });
  }

  function renderAudioFormats(presets) {
    audioFormatsGrid.innerHTML = '';
    let defaultPreset = presets.find(p => p.format_id === 'mp3-320') || presets[0];
    state.selectedAudioPreset = defaultPreset.format_id;

    presets.forEach(p => {
      const card = document.createElement('div');
      const isSelected = p.format_id === defaultPreset.format_id;
      card.className = `format-card ${isSelected ? 'selected' : ''}`;
      card.dataset.formatId = p.format_id;

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-extrabold text-xs sm:text-sm text-white">${p.title}</span>
        </div>
        <div class="text-[10px] text-slate-400 mt-0.5 truncate">${p.badge}</div>
        <div class="mt-1 flex items-center justify-between text-[10px] text-slate-400">
          <span class="uppercase font-bold text-purple-400">${p.codec}</span>
          <span class="font-mono text-cyan-300 font-medium">${p.filesize_str || 'Estimated'}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('#audio-formats-grid .format-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        state.selectedAudioPreset = p.format_id;
        updateDownloadButtonLabel();
      });

      audioFormatsGrid.appendChild(card);
    });
  }

  function updateDownloadButtonLabel() {
    if (state.selectedType === 'video') {
      const ext = state.selectedContainer.toUpperCase();
      downloadButtonLabel.textContent = `Download Video • ${ext} (${state.selectedResolution})`;
    } else {
      const preset = (state.analyzedMedia?.audio_formats || []).find(p => p.format_id === state.selectedAudioPreset);
      const title = preset ? preset.title : 'MP3 (320 kbps)';
      downloadButtonLabel.textContent = `Download Audio • ${title}`;
    }
  }

  // --- Start Download Handler ---
  async function handleStartDownload() {
    if (!state.analyzedMedia) {
      showError("Please analyze a valid link first.");
      return;
    }

    const customFilename = customFilenameInput.value.trim();
    let params = {
      url: state.analyzedMedia.url,
      type: state.selectedType,
      custom_filename: customFilename
    };

    if (state.selectedType === 'video') {
      params.quality = state.selectedResolution;
      params.container = state.selectedContainer;
    } else {
      const audioPreset = (state.analyzedMedia.audio_formats || []).find(p => p.format_id === state.selectedAudioPreset);
      params.quality = audioPreset ? audioPreset.format_id : 'mp3-320';
      params.container = audioPreset ? audioPreset.codec : 'mp3';
    }

    btnStartDownload.disabled = true;
    btnStartDownload.classList.add('opacity-70');

    try {
      const res = await API.startDownload(params);
      if (res.success && res.job_id) {
        showToast("Download started! Tracking progress below.", "success");
        state.activeJobs.set(res.job_id, res.job);
        renderActiveDownloads();
        listenToJobProgress(res.job_id);

        document.getElementById('active-downloads-section').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        showError("Failed to initiate download: " + (res.detail || "Server error"));
      }
    } catch (err) {
      showError("Download request failed: " + err.message);
    } finally {
      btnStartDownload.disabled = false;
      btnStartDownload.classList.remove('opacity-70');
    }
  }

  // --- Real-time Progress (SSE + Polling) ---
  function listenToJobProgress(jobId) {
    if (state.eventSources.has(jobId)) return;

    try {
      const sse = new EventSource(`/api/stream-progress/${jobId}`);
      state.eventSources.set(jobId, sse);

      sse.onmessage = (event) => {
        try {
          const job = JSON.parse(event.data);
          state.activeJobs.set(jobId, job);
          updateActiveDownloadCard(job);

          if (job.status === 'completed' || job.status === 'error' || job.status === 'cancelled') {
            sse.close();
            state.eventSources.delete(jobId);
            loadHistory();
            if (job.status === 'completed') {
              showToast(`"${job.title}" downloaded successfully!`, "success", 5000);
            }
          }
        } catch (e) {
          console.error("Error parsing progress update", e);
        }
      };

      sse.onerror = () => {
        sse.close();
        state.eventSources.delete(jobId);
      };
    } catch (err) {
      console.warn("SSE not available, relying on polling", err);
    }
  }

  function startJobPolling() {
    setInterval(async () => {
      if (state.activeJobs.size === 0) return;

      for (const [jobId, job] of state.activeJobs.entries()) {
        if (job.status === 'downloading' || job.status === 'queued' || job.status === 'processing') {
          try {
            const updated = await API.getProgress(jobId);
            if (updated) {
              state.activeJobs.set(jobId, updated);
              updateActiveDownloadCard(updated);
              if (updated.status === 'completed' || updated.status === 'error' || updated.status === 'cancelled') {
                loadHistory();
              }
            }
          } catch (e) {
            console.warn(`Polling error for ${jobId}`, e);
          }
        }
      }
    }, 1500);
  }

  // --- Render Active Downloads ---
  function renderActiveDownloads() {
    const list = activeDownloadsList;
    const noActiveMsg = document.getElementById('no-active-downloads');

    const runningJobs = Array.from(state.activeJobs.values()).filter(j => j.status !== 'completed');
    activeCountBadge.textContent = runningJobs.length;

    if (runningJobs.length === 0) {
      if (noActiveMsg) noActiveMsg.classList.remove('hidden');
      return;
    }

    if (noActiveMsg) noActiveMsg.classList.add('hidden');

    runningJobs.forEach(job => {
      let card = document.getElementById(`active-job-${job.id}`);
      if (!card) {
        card = createActiveJobCardElement(job);
        list.prepend(card);
      } else {
        updateActiveDownloadCard(job);
      }
    });

    lucide.createIcons();
  }

  function createActiveJobCardElement(job) {
    const card = document.createElement('div');
    card.id = `active-job-${job.id}`;
    card.className = 'glass-card p-3.5 space-y-2.5 border-purple-500/20';

    const isAudio = job.type === 'audio';
    const thumbHtml = renderThumbnailHtml(job.thumbnail, job.platform, job.container, isAudio, 'w-11 h-11');

    card.innerHTML = `
      <div class="flex items-start justify-between gap-2.5">
        <div class="flex items-center gap-2.5 flex-1 min-w-0">
          ${thumbHtml}
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 uppercase">${job.container}</span>
              <span class="text-[10px] text-slate-400 font-mono">${job.quality}</span>
            </div>
            <h4 class="text-xs sm:text-sm font-bold text-white truncate mt-0.5">${job.title}</h4>
          </div>
        </div>

        <button class="btn-cancel-job p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors shrink-0" title="Cancel Download">
          <i data-lucide="x-circle" class="w-4 h-4"></i>
        </button>
      </div>

      <!-- Animated Progress Bar -->
      <div class="space-y-1">
        <div class="w-full h-2 rounded-full bg-slate-900 overflow-hidden border border-white/5 relative">
          <div class="job-progress-bar h-full rounded-full bg-gradient-to-r from-purple-500 to-cyan-400 progress-bar-animated transition-all duration-300" style="width: ${job.progress || 0}%"></div>
        </div>
        <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono">
          <span class="job-status-pill text-cyan-400 font-sans font-semibold">${job.status === 'processing' ? 'FFmpeg Processing...' : 'Downloading...'}</span>
          <div class="flex items-center gap-2">
            <span class="job-speed">${job.speed_str || '0 B/s'}</span>
            <span class="job-eta">ETA: ${job.eta_str || '--:--'}</span>
            <span class="job-pct font-bold text-white">${job.progress || 0}%</span>
          </div>
        </div>
      </div>
    `;

    const cancelBtn = card.querySelector('.btn-cancel-job');
    cancelBtn.addEventListener('click', async () => {
      cancelBtn.disabled = true;
      try {
        await API.cancelJob(job.id);
        showToast("Download cancelled", "info");
      } catch (e) {
        console.error("Cancel failed", e);
      }
    });

    return card;
  }

  function updateActiveDownloadCard(job) {
    let card = document.getElementById(`active-job-${job.id}`);
    if (!card) {
      renderActiveDownloads();
      return;
    }

    const bar = card.querySelector('.job-progress-bar');
    const pct = card.querySelector('.job-pct');
    const speed = card.querySelector('.job-speed');
    const eta = card.querySelector('.job-eta');
    const statusPill = card.querySelector('.job-status-pill');

    if (bar) bar.style.width = `${job.progress || 0}%`;
    if (pct) pct.textContent = `${job.progress || 0}%`;
    if (speed) speed.textContent = job.speed_str || '0 B/s';
    if (eta) eta.textContent = `ETA: ${job.eta_str || '--:--'}`;

    if (statusPill) {
      if (job.status === 'processing') {
        statusPill.textContent = 'Merging & Transcoding...';
        statusPill.className = 'job-status-pill text-purple-400 font-semibold animate-pulse';
      } else if (job.status === 'completed') {
        statusPill.textContent = 'Complete!';
        statusPill.className = 'job-status-pill text-emerald-400 font-bold';
        setTimeout(() => {
          card.remove();
          renderActiveDownloads();
        }, 1500);
      } else if (job.status === 'error') {
        statusPill.textContent = `Error: ${job.error_message || 'Failed'}`;
        statusPill.className = 'job-status-pill text-red-400 font-semibold';
      } else if (job.status === 'cancelled') {
        statusPill.textContent = 'Cancelled';
        statusPill.className = 'job-status-pill text-slate-500 font-semibold';
        setTimeout(() => {
          card.remove();
          renderActiveDownloads();
        }, 1500);
      }
    }
  }

  // --- Download History Management (Mobile-First & Organized) ---
  async function loadHistory() {
    try {
      const res = await API.getHistory();
      state.historyItems = res.history || [];
      renderHistoryList();
    } catch (e) {
      console.warn("Failed to load history:", e);
    }
  }

  function renderHistoryList() {
    const list = historyList;
    const noHistoryMsg = document.getElementById('no-history-msg');

    // Filter items based on type & search query
    let filtered = state.historyItems.filter(item => {
      // Type filter
      if (state.historyFilter === 'video' && item.type === 'audio') return false;
      if (state.historyFilter === 'audio' && item.type !== 'audio') return false;

      // Search query
      if (state.historySearchQuery) {
        const q = state.historySearchQuery.toLowerCase();
        const titleMatch = (item.title || '').toLowerCase().includes(q);
        const platformMatch = (item.platform?.name || '').toLowerCase().includes(q);
        if (!titleMatch && !platformMatch) return false;
      }
      return true;
    });

    historyCountBadge.textContent = filtered.length;

    if (filtered.length === 0) {
      list.innerHTML = `
        <div class="glass-card p-6 text-center text-slate-500 text-xs">
          ${state.historyItems.length === 0 ? 'Your downloaded media history will appear here.' : 'No items match your filter criteria.'}
        </div>
      `;
      return;
    }

    list.innerHTML = '';

    filtered.forEach(item => {
      const card = document.createElement('div');
      card.className = 'glass-card p-3 sm:p-3.5 space-y-2.5 border-white/5 hover:border-purple-500/30 transition-all';

      const platform = item.platform || detectPlatform(item.url);
      const isAudio = item.type === 'audio' || (item.format && ['mp3', 'm4a', 'wav', 'flac'].includes(item.format.toLowerCase()));

      // Generate clean thumbnail with vector fallback
      const thumbHtml = renderThumbnailHtml(item.thumbnail, platform, item.format, isAudio, 'w-11 h-11 sm:w-12 sm:h-12');

      card.innerHTML = `
        <!-- Top Row: Thumbnail + Info -->
        <div class="flex items-center gap-2.5 sm:gap-3 min-w-0">
          ${thumbHtml}
          
          <div class="min-w-0 flex-1">
            <h4 class="text-xs sm:text-sm font-bold text-white truncate leading-snug">${item.title}</h4>
            <div class="flex items-center gap-1.5 sm:gap-2 mt-1 text-[10px] sm:text-[11px] text-slate-400 flex-wrap">
              <span class="inline-flex items-center gap-1 font-semibold" style="color: ${platform.color || '#A78BFA'};">
                <i data-lucide="${platform.icon || 'video'}" class="w-3 h-3"></i>
                <span>${platform.name}</span>
              </span>
              <span>•</span>
              <span class="font-mono text-cyan-300 font-semibold">${item.file_size_str || 'Downloaded'}</span>
              <span>•</span>
              <span>${item.created_at || 'Recently'}</span>
            </div>
          </div>
        </div>

        <!-- Bottom Action Toolbar (Mobile-Optimized) -->
        <div class="flex items-center gap-1.5 pt-1.5 border-t border-white/5">
          <!-- Play / Open File (Primary Action) -->
          <button class="btn-play-history flex-1 sm:flex-initial px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-200 text-xs font-bold flex items-center justify-center gap-1.5 border border-purple-500/30 transition-all active:scale-95" title="Play Media File">
            <i data-lucide="play" class="w-3 h-3 fill-current"></i>
            <span>Play</span>
          </button>

          <!-- Show in Folder -->
          <button class="btn-folder-history p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white border border-white/5 transition-all text-xs flex items-center gap-1 active:scale-95" title="Show in Folder">
            <i data-lucide="folder" class="w-3.5 h-3.5 text-cyan-400"></i>
            <span class="hidden sm:inline">Folder</span>
          </button>

          <!-- Save to Browser -->
          <a href="/api/file/${item.id}" download class="p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 text-slate-300 hover:text-white border border-white/5 transition-all text-xs flex items-center gap-1 active:scale-95" title="Download to Browser">
            <i data-lucide="download" class="w-3.5 h-3.5 text-emerald-400"></i>
            <span class="hidden sm:inline">Save</span>
          </a>

          <!-- Delete from History -->
          <button class="btn-delete-history p-1.5 rounded-lg hover:bg-red-950/40 text-slate-400 hover:text-red-400 transition-all ml-auto active:scale-95" title="Remove from list">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;

      // Event Listeners for History Card
      const playBtn = card.querySelector('.btn-play-history');
      playBtn.addEventListener('click', async () => {
        if (!item.file_path) {
          showToast("File path is unavailable", "error");
          return;
        }
        try {
          await API.openFile(item.file_path);
        } catch (e) {
          showToast("Failed to launch media player: " + e.message, "error");
        }
      });

      const folderBtn = card.querySelector('.btn-folder-history');
      folderBtn.addEventListener('click', async () => {
        try {
          await API.openFolder(item.file_path);
        } catch (e) {
          showToast("Failed to open folder: " + e.message, "error");
        }
      });

      const deleteBtn = card.querySelector('.btn-delete-history');
      deleteBtn.addEventListener('click', async () => {
        try {
          await API.deleteHistoryItem(item.id, false);
          card.remove();
          showToast("Item removed from history", "info");
          loadHistory();
        } catch (e) {
          showToast("Failed to remove item: " + e.message, "error");
        }
      });

      list.appendChild(card);
    });

    lucide.createIcons();
  }

  // --- Setup Event Listeners ---
  function setupEventListeners() {
    urlInput.addEventListener('input', updateInputIcon);

    urlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleAnalyze();
    });

    btnClearUrl.addEventListener('click', () => {
      urlInput.value = '';
      updateInputIcon();
      hideError();
      urlInput.focus();
    });

    btnPasteClipboard.addEventListener('click', async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text) {
          urlInput.value = text.trim();
          updateInputIcon();
          handleAnalyze();
        } else {
          showToast("Clipboard is empty", "info");
        }
      } catch (err) {
        showToast("Please paste the link manually into the box.", "info");
      }
    });

    btnAnalyze.addEventListener('click', handleAnalyze);
    btnCloseError.addEventListener('click', hideError);

    // Format category tabs
    tabVideo.addEventListener('click', () => {
      state.selectedType = 'video';
      tabVideo.className = 'flex-1 py-2 px-3 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition-all bg-purple-600 text-white shadow-md active:scale-98';
      tabAudio.className = 'flex-1 py-2 px-3 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition-all text-slate-400 hover:text-white active:scale-98';
      panelVideo.classList.remove('hidden');
      panelAudio.classList.add('hidden');
      updateDownloadButtonLabel();
    });

    tabAudio.addEventListener('click', () => {
      state.selectedType = 'audio';
      tabAudio.className = 'flex-1 py-2 px-3 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition-all bg-purple-600 text-white shadow-md active:scale-98';
      tabVideo.className = 'flex-1 py-2 px-3 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition-all text-slate-400 hover:text-white active:scale-98';
      panelAudio.classList.remove('hidden');
      panelVideo.classList.add('hidden');
      updateDownloadButtonLabel();
    });

    // Container toggles (MP4 / MKV)
    btnExtMp4.addEventListener('click', () => {
      state.selectedContainer = 'mp4';
      btnExtMp4.className = 'px-2 py-0.5 rounded-md text-[11px] font-bold bg-purple-600 text-white';
      btnExtMkv.className = 'px-2 py-0.5 rounded-md text-[11px] font-bold text-slate-400 hover:text-white';
      updateDownloadButtonLabel();
    });

    btnExtMkv.addEventListener('click', () => {
      state.selectedContainer = 'mkv';
      btnExtMkv.className = 'px-2 py-0.5 rounded-md text-[11px] font-bold bg-purple-600 text-white';
      btnExtMp4.className = 'px-2 py-0.5 rounded-md text-[11px] font-bold text-slate-400 hover:text-white';
      updateDownloadButtonLabel();
    });

    btnToggleFilename.addEventListener('click', () => {
      customFilenameBox.classList.toggle('hidden');
      if (!customFilenameBox.classList.contains('hidden')) {
        customFilenameInput.focus();
      }
    });

    btnStartDownload.addEventListener('click', handleStartDownload);

    btnOpenDownloadDir.addEventListener('click', async () => {
      try {
        await API.openFolder('');
        showToast("Opening Downloads folder...", "info");
      } catch (e) {
        showToast("Error opening folder: " + e.message, "error");
      }
    });

    // History controls
    btnRefreshHistory.addEventListener('click', () => {
      loadHistory();
      showToast("History refreshed", "info");
    });

    btnClearHistory.addEventListener('click', async () => {
      if (confirm("Clear all download history records?")) {
        try {
          await API.clearHistory();
          loadHistory();
          showToast("History cleared", "info");
        } catch (e) {
          showToast("Failed to clear history: " + e.message, "error");
        }
      }
    });

    // History search and filters
    if (historySearchInput) {
      historySearchInput.addEventListener('input', (e) => {
        state.historySearchQuery = e.target.value.trim();
        renderHistoryList();
      });
    }

    if (filterAll && filterVideo && filterAudio) {
      filterAll.addEventListener('click', () => {
        state.historyFilter = 'all';
        filterAll.className = 'px-2.5 py-1 rounded-md bg-purple-600 text-white transition-all';
        filterVideo.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white transition-all';
        filterAudio.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white transition-all';
        renderHistoryList();
      });

      filterVideo.addEventListener('click', () => {
        state.historyFilter = 'video';
        filterVideo.className = 'px-2.5 py-1 rounded-md bg-purple-600 text-white transition-all';
        filterAll.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white transition-all';
        filterAudio.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white transition-all';
        renderHistoryList();
      });

      filterAudio.addEventListener('click', () => {
        state.historyFilter = 'audio';
        filterAudio.className = 'px-2.5 py-1 rounded-md bg-purple-600 text-white transition-all';
        filterAll.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white transition-all';
        filterVideo.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white transition-all';
        renderHistoryList();
      });
    }

    // Settings Modal
    btnOpenSettings.addEventListener('click', () => settingsModal.classList.remove('hidden'));
    btnCloseSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));
    btnCancelSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));

    btnSettingsOpenDir.addEventListener('click', async () => {
      const dir = settingsDownloadDir.value.trim();
      await API.openFolder(dir);
    });

    btnSaveSettings.addEventListener('click', async () => {
      const newSettings = {
        download_dir: settingsDownloadDir.value.trim(),
        browser_cookies: settingsBrowserCookies.value,
        embed_metadata: settingsEmbedMetadata.checked,
        embed_thumbnail: settingsEmbedThumbnail.checked
      };

      try {
        const res = await API.saveSettings(newSettings);
        if (res.success) {
          state.settings = res.settings;
          settingsModal.classList.add('hidden');
          showToast("Settings successfully saved!", "success");
        }
      } catch (e) {
        showToast("Failed to save settings: " + e.message, "error");
      }
    });
  }

  // Run initialization
  init();
});
