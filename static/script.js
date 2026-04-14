class APIManager {
    constructor() {
        this.endpoints = [];
        this.currentEndpoint = null;
        this.categories = new Set();
        this.uploadedFiles = [];
        this.currentResponseData = null;
        this.currentMedia = null;
        this.sidebarVisible = false;
        this.init();
    }

    async init() {
        await this.loadUserIP();
        await this.loadEndpoints();
        this.setupEventListeners();
        this.setupSidebarToggle();
        this.setupMediaModal();
    }

    setupMediaModal() {
        const modal = document.getElementById('mediaModal');
        const closeBtn = document.querySelector('.modal-close');
        const shareBtn = document.querySelector('.modal-share');
        const downloadBtn = document.querySelector('.modal-download');

        if (closeBtn && modal) closeBtn.onclick = () => modal.style.display = 'none';
        if (modal) {
            modal.onclick = (e) => {
                if (e.target === modal) modal.style.display = 'none';
            };
        }

        if (shareBtn) {
            shareBtn.onclick = () => this.shareCurrentMedia();
        }

        if (downloadBtn) {
            downloadBtn.onclick = () => this.downloadCurrentMedia();
        }
    }

    setupSidebarToggle() {
        const toggle = document.getElementById('menuToggleBtn');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if (!toggle || !sidebar) return;

        const updateButtonText = () => {
            toggle.innerHTML = this.sidebarVisible
                ? '<i class="fas fa-times"></i> Ocultar Menú'
                : '<i class="fas fa-bars"></i> Mostrar Menú';
        };

        const closeSidebar = () => {
            this.sidebarVisible = false;
            sidebar.classList.add('hidden');
            if (overlay) overlay.classList.remove('active');
            updateButtonText();
        };

        const openSidebar = () => {
            this.sidebarVisible = true;
            sidebar.classList.remove('hidden');
            if (overlay) overlay.classList.add('active');
            updateButtonText();
        };

        sidebar.classList.add('hidden');
        this.sidebarVisible = false;
        updateButtonText();

        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.sidebarVisible) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });

        if (overlay) {
            overlay.addEventListener('click', () => {
                closeSidebar();
            });
        }

        document.addEventListener('click', (e) => {
            if (this.sidebarVisible && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
                closeSidebar();
            }
        });
    }

    async loadUserIP() {
        try {
            const res = await fetch('https://api.ipify.org?format=json');
            const data = await res.json();
            const ipEl = document.getElementById('user-ip');
            if (ipEl) ipEl.textContent = data.ip;
        } catch {
            const ipEl = document.getElementById('user-ip');
            if (ipEl) ipEl.textContent = 'desconocida';
        }
    }

    async loadEndpoints() {
        try {
            const start = Date.now();
            const res = await fetch('/api/list');
            const json = await res.json();
            if (json.status && json.data) {
                this.endpoints = json.data;
                const liveResp = document.getElementById('live-response');
                const apiCount = document.getElementById('api-count');
                const endpointCount = document.getElementById('endpoint-count');
                const statEndpoints = document.getElementById('stat-endpoints');
                if (liveResp) liveResp.textContent = (Date.now() - start) + 'ms';
                if (apiCount) apiCount.textContent = this.endpoints.length;
                if (endpointCount) endpointCount.textContent = this.endpoints.length;
                if (statEndpoints) statEndpoints.textContent = this.endpoints.length;
                this.extractCategories();
                this.renderSidebar();
                const statCategories = document.getElementById('stat-categories');
                if (statCategories) statCategories.textContent = this.categories.size;
            }
        } catch (error) {
            console.error('Error:', error);
            const endpointList = document.getElementById('endpoint-list');
            if (endpointList) endpointList.innerHTML = '<div class="loading-placeholder">Error al cargar endpoints</div>';
        }
    }

    extractCategories() {
        this.categories.clear();
        this.endpoints.forEach(e => {
            if (e.category) this.categories.add(e.category);
        });
    }

    renderSidebar() {
        const list = document.getElementById('endpoint-list');
        if (!list) return;
        const cats = {};
        this.endpoints.forEach(e => {
            if (!cats[e.category]) cats[e.category] = [];
            cats[e.category].push(e);
        });

        let html = '';
        for (let cat in cats) {
            html += `<div class="category-section" data-category="${cat.toLowerCase()}">`;
            html += `<div class="category-header"><i class="far fa-folder-open"></i><span>${cat}</span><span class="endpoint-badge">${cats[cat].length}</span><i class="fas fa-chevron-down"></i></div>`;
            html += `<div class="endpoints-list">`;
            cats[cat].forEach(e => {
                html += `<div class="endpoint-item" data-endpoint="${e.endpoint}" data-method="${e.method}" data-category="${cat.toLowerCase()}" data-name="${e.name.toLowerCase()}">`;
                html += `<div class="endpoint-method method-${e.method.toLowerCase()}">${e.method}</div>`;
                html += `<div class="endpoint-info"><div class="endpoint-name">${e.name}</div><div class="endpoint-path">${e.endpoint}</div></div>`;
                html += `</div>`;
            });
            html += `</div></div>`;
        }
        list.innerHTML = html;

        document.querySelectorAll('.endpoint-item').forEach(el => {
            el.addEventListener('click', () => {
                const endpoint = this.endpoints.find(ep => ep.endpoint === el.dataset.endpoint);
                if (endpoint) this.loadEndpoint(endpoint);
                document.querySelectorAll('.endpoint-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
                if (this.sidebarVisible) {
                    const sidebar = document.getElementById('sidebar');
                    const overlay = document.getElementById('sidebarOverlay');
                    if (sidebar) sidebar.classList.add('hidden');
                    if (overlay) overlay.classList.remove('active');
                    this.sidebarVisible = false;
                    const toggle = document.getElementById('menuToggleBtn');
                    if (toggle) toggle.innerHTML = '<i class="fas fa-bars"></i> Mostrar Menú';
                }
            });
        });

        document.querySelectorAll('.category-header').forEach(h => {
            h.addEventListener('click', (e) => {
                e.stopPropagation();
                const listEl = h.nextElementSibling;
                const arrow = h.querySelector('.fas.fa-chevron-down');
                if (listEl && arrow) {
                    if (listEl.style.display === 'none') {
                        listEl.style.display = 'flex';
                        arrow.style.transform = 'rotate(0deg)';
                    } else {
                        listEl.style.display = 'none';
                        arrow.style.transform = 'rotate(-90deg)';
                    }
                }
            });
        });

        this.renderCategoryFilters();
        this.setupSearch();
    }

    renderCategoryFilters() {
        const container = document.getElementById('category-filters');
        if (!container) return;
        let html = `<button class="pill-btn active" data-filter="all">Todos</button>`;
        this.categories.forEach(cat => {
            html += `<button class="pill-btn" data-filter="${cat.toLowerCase()}">${cat}</button>`;
        });
        container.innerHTML = html;

        container.querySelectorAll('.pill-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const filter = btn.dataset.filter;
                document.querySelectorAll('.category-section').forEach(s => {
                    s.style.display = (filter === 'all' || s.dataset.category === filter) ? 'block' : 'none';
                });
            });
        });
    }

    setupSearch() {
        const searchInput = document.getElementById('endpoint-search');
        if (!searchInput) return;
        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            document.querySelectorAll('.category-section').forEach(cat => {
                let any = false;
                cat.querySelectorAll('.endpoint-item').forEach(item => {
                    const match = item.textContent.toLowerCase().includes(term);
                    item.style.display = match ? 'flex' : 'none';
                    if (match) any = true;
                });
                cat.style.display = any || term === '' ? 'block' : 'none';
            });
        });
    }

    loadEndpoint(ep) {
        this.currentEndpoint = ep;
        const dashboardView = document.getElementById('dashboard-view');
        const detailView = document.getElementById('detail-view');
        const detailName = document.getElementById('detail-name');
        const detailMethod = document.getElementById('detail-method');
        const apiMethod = document.getElementById('api-method');
        const apiPath = document.getElementById('api-path');
        const apiDescription = document.getElementById('api-description');
        const tryUrl = document.getElementById('try-url');
        const tryMethod = document.getElementById('try-method');

        if (dashboardView) dashboardView.style.display = 'none';
        if (detailView) detailView.style.display = 'block';
        if (detailName) detailName.textContent = ep.name || ep.endpoint;
        if (detailMethod) detailMethod.textContent = ep.method;
        if (apiMethod) {
            apiMethod.textContent = ep.method;
            apiMethod.className = `method-tag method-${ep.method.toLowerCase()}`;
        }
        if (apiPath) apiPath.textContent = ep.endpoint;
        if (apiDescription) apiDescription.textContent = ep.description || 'Sin descripción disponible.';

        const baseUrl = window.location.origin;
        if (tryUrl) tryUrl.value = baseUrl + ep.endpoint;
        if (tryMethod) tryMethod.value = ep.method;

        const tbody = document.querySelector('#parameters-table tbody');
        if (tbody) {
            if (!ep.parameters || ep.parameters.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="empty-table">No requiere parámetros</td></tr>';
            } else {
                tbody.innerHTML = ep.parameters.map(p => `
                    <tr>
                        <td><strong>${p.name}</strong> ${p.required ? '<span class="required-badge">req</span>' : ''}</td>
                        <td>${p.description || '-'}</td>
                        <td>${p.required ? 'requerido' : 'opcional'}</td>
                        <td><code>${p.example || '-'}</code></td>
                    </tr>
                `).join('');
            }
        }

        const exampleUrl = baseUrl + ep.endpoint + (ep.parameters?.find(p => p.example) ? '?' + ep.parameters.filter(p => p.example).map(p => `${p.name}=${encodeURIComponent(p.example)}`).join('&') : '');
        const curlCode = document.getElementById('curl-code');
        const jsCode = document.getElementById('js-code');
        const pythonCode = document.getElementById('python-code');
        if (curlCode) curlCode.textContent = `curl -X ${ep.method} "${exampleUrl}"`;
        if (jsCode) jsCode.textContent = `fetch('${exampleUrl}', { method: '${ep.method}' })\n  .then(r => r.json())\n  .then(console.log)\n  .catch(console.error);`;
        if (pythonCode) pythonCode.textContent = `import requests\n\nresponse = requests.${ep.method.toLowerCase()}('${exampleUrl}')\nprint(response.json())`;

        const paramsDiv = document.getElementById('try-params-container');
        if (paramsDiv) {
            if (!ep.parameters || ep.parameters.length === 0) {
                paramsDiv.innerHTML = '<div class="info-note">Este endpoint no requiere parámetros.</div>';
            } else {
                paramsDiv.innerHTML = ep.parameters.map(p => `
                    <div class="param-row">
                        <label>${p.name} ${p.required ? '<span class="required-badge">req</span>' : ''}</label>
                        <input type="text" id="param-${p.name}" placeholder="${p.description || ''}" value="${p.example || ''}" data-param="${p.name}">
                        <div class="param-desc">${p.description || ''}</div>
                    </div>
                `).join('');
            }
        }

        const uploadSec = document.getElementById('upload-section');
        if (uploadSec) uploadSec.style.display = ep.supportsUpload ? 'block' : 'none';

        this.clearResponse();
        setTimeout(() => {
            if (typeof hljs !== 'undefined') hljs.highlightAll();
        }, 100);
    }

    clearResponse() {
        const responseStatus = document.getElementById('response-status');
        const responseTime = document.getElementById('response-time');
        const tryResponseBody = document.getElementById('try-response-body');
        const responseActions = document.getElementById('response-actions');
        const mediaSection = document.getElementById('media-section');
        const jsonMediaSection = document.getElementById('json-media-section');
        const mediaPreview = document.getElementById('media-preview');
        const jsonMediaContainer = document.getElementById('json-media-container');

        if (responseStatus) responseStatus.textContent = '-';
        if (responseTime) responseTime.textContent = '-';
        if (tryResponseBody) tryResponseBody.innerHTML = '<code class="language-json">// La respuesta aparecerá aquí</code>';
        if (responseActions) responseActions.style.display = 'none';
        if (mediaSection) mediaSection.style.display = 'none';
        if (jsonMediaSection) jsonMediaSection.style.display = 'none';
        if (mediaPreview) mediaPreview.innerHTML = '';
        if (jsonMediaContainer) jsonMediaContainer.innerHTML = '';
        this.currentResponseData = null;
        this.currentMedia = null;
    }

    buildFullUrl() {
        if (!this.currentEndpoint) return '';
        const base = window.location.origin + this.currentEndpoint.endpoint;
        const params = {};
        document.querySelectorAll('#try-params-container input[type="text"]').forEach(i => {
            if (i.value.trim()) params[i.dataset.param] = i.value;
        });
        return Object.keys(params).length > 0 ? base + '?' + new URLSearchParams(params).toString() : base;
    }

    extractMediaUrls(obj, media = []) {
        if (!obj || typeof obj !== 'object') return media;
        if (Array.isArray(obj)) {
            obj.forEach(item => this.extractMediaUrls(item, media));
        } else {
            for (let key in obj) {
                const value = obj[key];
                if (typeof value === 'string' && (value.match(/\.(jpg|jpeg|png|gif|webp|mp4|webm|mp3)(\?.*)?$/i) || value.includes('image'))) {
                    media.push({ url: value, type: value.match(/\.(mp4|webm)/i) ? 'video' : value.match(/\.mp3/i) ? 'audio' : 'image' });
                } else if (typeof value === 'object' && value !== null) {
                    this.extractMediaUrls(value, media);
                }
            }
        }
        return media;
    }

    setupEventListeners() {
        const backBtn = document.getElementById('backBtn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                const dashboardView = document.getElementById('dashboard-view');
                const detailView = document.getElementById('detail-view');
                if (dashboardView) dashboardView.style.display = 'block';
                if (detailView) detailView.style.display = 'none';
                this.clearResponse();
            });
        }

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
                const tabPane = document.getElementById(btn.dataset.tab + '-tab');
                if (tabPane) tabPane.classList.add('active');
            });
        });

        document.querySelectorAll('.copy-button').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = document.getElementById(btn.dataset.target);
                if (target) {
                    navigator.clipboard.writeText(target.textContent);
                    this.showMsg('Copiado', 'success');
                }
            });
        });

        const copyFullUrlBtn = document.getElementById('copyFullUrlBtn');
        if (copyFullUrlBtn) {
            copyFullUrlBtn.addEventListener('click', () => {
                if (this.currentEndpoint) {
                    navigator.clipboard.writeText(this.buildFullUrl());
                    this.showMsg('URL copiada', 'success');
                }
            });
        }

        const shareEndpointBtn = document.getElementById('shareEndpointBtn');
        if (shareEndpointBtn) {
            shareEndpointBtn.addEventListener('click', () => {
                if (this.currentEndpoint && navigator.share) {
                    navigator.share({ title: this.currentEndpoint.name, url: this.buildFullUrl() });
                }
            });
        }

        const sendRequest = document.getElementById('send-request');
        if (sendRequest) sendRequest.addEventListener('click', () => this.sendRequest());

        const copyJsonBtn = document.getElementById('copy-json-btn');
        if (copyJsonBtn) {
            copyJsonBtn.addEventListener('click', () => {
                if (this.currentResponseData) {
                    navigator.clipboard.writeText(this.currentResponseData);
                    this.showMsg('Respuesta copiada', 'success');
                }
            });
        }

        const openApiBtn = document.getElementById('open-api-btn');
        if (openApiBtn) openApiBtn.addEventListener('click', () => window.open(this.buildFullUrl(), '_blank'));

        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-upload');
        const browseBtn = document.getElementById('browse-btn');

        if (browseBtn && fileInput) browseBtn.addEventListener('click', (e) => { e.preventDefault(); fileInput.click(); });
        if (uploadArea && fileInput) uploadArea.addEventListener('click', () => fileInput.click());
        if (fileInput) fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => e.preventDefault());
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                if (e.dataTransfer.files.length) this.handleFiles(e.dataTransfer.files);
            });
        }
    }

    handleFiles(files) {
        this.uploadedFiles = Array.from(files);
        const preview = document.getElementById('file-preview');
        if (!preview) return;
        if (this.uploadedFiles.length === 0) {
            preview.innerHTML = '';
            return;
        }
        preview.innerHTML = this.uploadedFiles.map((f, i) => `
            <div class="file-item">
                <i class="far fa-file"></i>
                <span>${f.name.substring(0, 20)}</span>
                <button class="file-remove" data-index="${i}"><i class="fas fa-times"></i></button>
            </div>
        `).join('');
        preview.querySelectorAll('.file-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.dataset.index);
                this.uploadedFiles.splice(idx, 1);
                this.handleFiles(this.uploadedFiles);
            });
        });
    }

    async sendRequest() {
        if (!this.currentEndpoint) return;

        const method = document.getElementById('try-method')?.value || 'GET';
        let url = document.getElementById('try-url')?.value || '';
        const params = {};
        document.querySelectorAll('#try-params-container input[type="text"]').forEach(i => {
            if (i.value.trim()) params[i.dataset.param] = i.value;
        });

        const start = Date.now();
        const loader = document.getElementById('response-loader');
        const respBody = document.getElementById('try-response-body');

        if (loader) loader.style.display = 'flex';
        if (respBody) respBody.innerHTML = '<code>// Cargando...</code>';
        const responseStatus = document.getElementById('response-status');
        const responseTime = document.getElementById('response-time');
        if (responseStatus) responseStatus.textContent = '-';
        if (responseTime) responseTime.textContent = '-';

        try {
            const options = { method, signal: AbortSignal.timeout(30000) };

            if (this.uploadedFiles.length > 0) {
                const fd = new FormData();
                this.uploadedFiles.forEach(f => fd.append('files', f));
                Object.keys(params).forEach(k => fd.append(k, params[k]));
                options.body = fd;
            } else if (['POST', 'PUT', 'PATCH'].includes(method) && Object.keys(params).length > 0) {
                options.headers = { 'Content-Type': 'application/json' };
                options.body = JSON.stringify(params);
            }

            if (method === 'GET' && Object.keys(params).length > 0) {
                url += '?' + new URLSearchParams(params).toString();
            }

            const res = await fetch(url, options);
            const time = Date.now() - start;
            if (responseStatus) responseStatus.textContent = res.status;
            if (responseTime) responseTime.textContent = time;

            const ct = res.headers.get('content-type') || '';

            if (ct.includes('application/json')) {
                const data = await res.json();
                this.currentResponseData = JSON.stringify(data, null, 2);
                if (respBody) respBody.innerHTML = `<code class="language-json">${this.escapeHtml(this.currentResponseData)}</code>`;
                const responseActions = document.getElementById('response-actions');
                if (responseActions) responseActions.style.display = 'flex';

                const media = this.extractMediaUrls(data);
                const jsonMediaSection = document.getElementById('json-media-section');
                const jsonMediaContainer = document.getElementById('json-media-container');
                if (media.length > 0 && jsonMediaContainer) {
                    jsonMediaContainer.innerHTML = media.slice(0, 6).map((m) => `
                        <div class="json-media-item">
                            ${m.type === 'image' ? `<img src="${m.url}" class="json-media-thumb" onerror="this.style.display='none'">` : `<div class="json-media-thumb video-thumb"><i class="fas fa-${m.type === 'video' ? 'video' : 'music'}"></i></div>`}
                            <div class="json-media-actions">
                                <button class="json-media-btn" data-url="${m.url}" data-type="${m.type}">Ver</button>
                            </div>
                        </div>
                    `).join('');
                    if (jsonMediaSection) jsonMediaSection.style.display = 'block';
                    jsonMediaContainer.querySelectorAll('.json-media-btn').forEach(btn => {
                        btn.addEventListener('click', () => this.openMediaModal(btn.dataset.url, btn.dataset.type));
                    });
                }
            } else if (ct.includes('image/')) {
                const blob = await res.blob();
                const blobUrl = URL.createObjectURL(blob);
                const mediaPreview = document.getElementById('media-preview');
                this.currentMedia = {
                    url: blobUrl,
                    blob,
                    type: 'image',
                    title: this.currentEndpoint?.name || 'Archivo'
                };
                if (mediaPreview) {
                    mediaPreview.innerHTML = `<img src="${blobUrl}" onclick="window.apimanager.openMediaModal('${blobUrl}', 'image')">`;
                }
                const mediaSection = document.getElementById('media-section');
                if (mediaSection) mediaSection.style.display = 'block';
                const responseActions = document.getElementById('response-actions');
                if (responseActions) responseActions.style.display = 'flex';
                if (respBody) respBody.innerHTML = '<code>// Respuesta multimedia</code>';
            } else {
                const text = await res.text();
                this.currentResponseData = text;
                if (respBody) respBody.innerHTML = `<code>${this.escapeHtml(text)}</code>`;
                const responseActions = document.getElementById('response-actions');
                if (responseActions) responseActions.style.display = 'flex';
            }

            if (typeof hljs !== 'undefined') hljs.highlightAll();
        } catch (err) {
            if (respBody) respBody.innerHTML = `<code class="language-json">${JSON.stringify({ error: err.message }, null, 2)}</code>`;
            if (responseStatus) responseStatus.textContent = 'Error';
            const responseActions = document.getElementById('response-actions');
            if (responseActions) responseActions.style.display = 'flex';
        } finally {
            if (loader) loader.style.display = 'none';
        }
    }

    openMediaModal(url, type) {
        const modal = document.getElementById('mediaModal');
        const container = document.getElementById('modalMediaContainer');
        this.currentMedia = {
            url,
            type,
            title: this.currentEndpoint?.name || 'Archivo'
        };
        if (!modal || !container) return;

        if (type === 'image') {
            container.innerHTML = `<img src="${url}">`;
        } else if (type === 'video') {
            container.innerHTML = `<video src="${url}" controls autoplay style="max-width:90%;max-height:90%;"></video>`;
        } else {
            container.innerHTML = `<audio src="${url}" controls autoplay style="width:80%;"></audio>`;
        }

        modal.style.display = 'block';
    }

    async fetchBlobAsFile(url, filename = 'archivo') {
        const res = await fetch(url);
        const blob = await res.blob();
        const ext = blob.type ? (blob.type.split('/')[1] || 'bin') : 'bin';
        return new File([blob], `${filename}.${ext}`, { type: blob.type || 'application/octet-stream' });
    }

    async shareCurrentMedia() {
        if (!this.currentMedia?.url) {
            this.showMsg('No hay archivo para compartir', 'error');
            return;
        }
        await this.shareMedia(this.currentMedia.url, this.currentMedia.title || 'Archivo');
    }

    async downloadCurrentMedia() {
        if (!this.currentMedia?.url) return;
        const a = document.createElement('a');
        a.href = this.currentMedia.url;
        a.download = this.currentMedia.title ? `${this.currentMedia.title}` : 'archivo';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    async shareMedia(url, title = 'Archivo') {
        try {
            if (!navigator.share) {
                this.showMsg('Tu navegador no soporta compartir', 'error');
                return;
            }

            const file = await this.fetchBlobAsFile(url, title);

            if (navigator.canShare && !navigator.canShare({ files: [file] })) {
                this.showMsg('Este navegador no permite compartir ese archivo', 'error');
                return;
            }

            await navigator.share({
                title,
                text: title,
                files: [file]
            });

            this.showMsg('Compartido', 'success');
        } catch (err) {
            if (err.name !== 'AbortError') {
                this.showMsg('No se pudo compartir', 'error');
            }
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showMsg(text, type) {
        const msg = document.createElement('div');
        msg.className = `message ${type}`;
        msg.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${text}`;
        msg.style.cssText = 'position:fixed;top:20px;right:20px;background:#212121;border:1px solid #3a3a3a;border-radius:30px;padding:10px 20px;z-index:10000;';
        document.body.appendChild(msg);
        setTimeout(() => msg.remove(), 2500);
    }
}

if (document.getElementById('sidebar')) {
    window.apimanager = new APIManager();
                  }
