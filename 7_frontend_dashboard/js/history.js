/*
 * history.js - Dynamic History page
 * Fetches /history via ApiClient.getHistory and renders dynamic analytics
 * Requirements:
 * - No hardcoded organism names
 * - All metrics derived from backend response
 * - Safe handling of missing fields
 */

(function () {
    const POLL_INTERVAL_MS = 8000; // Poll for new history every 8s

    document.addEventListener('DOMContentLoaded', () => {
        bindUI();
        fetchHistory();
        // Poll so the history updates automatically when new uploads arrive
        setInterval(() => fetchHistory(false), POLL_INTERVAL_MS);
    });

    function bindUI() {
        const limit = document.getElementById('historyLimit');
        if (limit) {
            limit.addEventListener('change', () => fetchHistory());
        }
        const refresh = document.getElementById('refreshBtn');
        if (refresh) refresh.addEventListener('click', () => fetchHistory());
    }

    async function fetchHistory(showLoading = true) {
        const container = document.getElementById('historyList');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const limitEl = document.getElementById('historyLimit');
        const limit = limitEl ? parseInt(limitEl.value, 10) || 50 : 50;

        if (!container) return;

        try {
            if (showLoading) {
                container.innerHTML = '<p style="text-align: center; color: #999; padding: 28px;">Loading history...</p>';
            }
            if (loadingIndicator) loadingIndicator.style.display = 'inline';

            const rows = await ApiClient.getHistory(limit);

            if (!rows || rows.length === 0) {
                // Fallback empty state
                renderEmptyState();
                return;
            }

            // Ensure rows is an array
            const data = Array.isArray(rows) ? rows : (rows.history || []);

            // Sort newest first by timestamp-like fields (try multiple possible keys)
            data.sort((a, b) => {
                const ta = parseTimestamp(a);
                const tb = parseTimestamp(b);
                return tb - ta;
            });

            // Update analytics and UI
            updateAll(data);
        } catch (err) {
            console.error('Failed to load history', err);
            const containerInner = document.getElementById('historyList');
            if (containerInner) containerInner.innerHTML = `<div style="padding:20px;background:#FEE;border-radius:8px;color:#C33">Error loading history: ${err.message}</div>`;
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        }
    }

    function parseTimestamp(item) {
        // Try multiple field names commonly used
        const ts = item.timestamp || item.created_at || item.time || item.date || item.ts;
        const parsed = ts ? Date.parse(ts) : NaN;
        return isNaN(parsed) ? 0 : parsed;
    }

    function updateAll(rows) {
        const metrics = computeMetrics(rows);
        updateStats(metrics);
        updateMostDetected(metrics);
        updateSafeUnsafe(metrics);
        updateRecentActivity(rows);
        updateImageGrid(rows);
        // Make all sections visible
        const statsSection = document.getElementById('stats-section');
        if (statsSection) statsSection.style.display = 'block';
        const chartsSection = document.getElementById('charts-section');
        if (chartsSection) chartsSection.style.display = 'block';
        const confSection = document.getElementById('confidence-section');
        if (confSection) confSection.style.display = 'block';
        const recentSection = document.getElementById('recent-section');
        if (recentSection) recentSection.style.display = 'block';
    }

    // Compute metrics entirely from backend rows
    function computeMetrics(rows) {
        const metrics = {
            total: rows.length,
            safe: 0,
            unsafe: 0,
            organismCounts: {}, // name -> count
            confidences: [],
        };

        rows.forEach(row => {
            // Safety/Verdit handling
            const verdict = extractFieldValue(row, ['verdict', 'overall_verdict', 'status']);
            if (typeof verdict === 'string') {
                const v = verdict.toLowerCase();
                if (v === 'safe' || v.includes('safe')) metrics.safe++;
                else if (v === 'unsafe' || v.includes('unsafe')) metrics.unsafe++;
            }

            // Extract confidences
            const confidences = extractConfidences(row);
            if (confidences.length > 0) {
                confidences.forEach(c => metrics.confidences.push(safeNumber(c)));
            }

            // Extract organism names and counts
            const countsObj = extractCountsObject(row);
            if (countsObj && typeof countsObj === 'object' && Object.keys(countsObj).length > 0) {
                Object.entries(countsObj).forEach(([name, cnt]) => {
                    const count = Number(cnt) || 0;
                    metrics.organismCounts[name] = (metrics.organismCounts[name] || 0) + count;
                });
            } else {
                // Fall back to single organism fields or detection arrays
                const names = extractOrganismNames(row);
                names.forEach(n => {
                    metrics.organismCounts[n] = (metrics.organismCounts[n] || 0) + 1;
                });
            }
        });

        // Confidence summary
        if (metrics.confidences.length > 0) {
            const sum = metrics.confidences.reduce((a, b) => a + b, 0);
            metrics.avg = sum / metrics.confidences.length;
            metrics.high = Math.max(...metrics.confidences);
            metrics.low = Math.min(...metrics.confidences);
        } else {
            metrics.avg = NaN;
            metrics.high = 0;
            metrics.low = 0;
        }

        return metrics;
    }

    function safeNumber(v) {
        const n = Number(v);
        return isNaN(n) ? 0 : n;
    }

    function extractFieldValue(obj, keys) {
        for (const k of keys) {
            if (!obj) continue;
            if (obj[k] !== undefined && obj[k] !== null) return obj[k];
            // nested overall_verdict.verdict
            if (typeof obj[k] === 'object' && obj[k] !== null && obj[k].verdict) return obj[k].verdict;
        }
        return undefined;
    }

    function extractConfidences(row) {
        const confs = [];
        if (row.confidence !== undefined && row.confidence !== null) confs.push(row.confidence);
        if (Array.isArray(row.detections)) {
            row.detections.forEach(d => { if (d.confidence !== undefined && d.confidence !== null) confs.push(d.confidence); });
        }
        if (Array.isArray(row.preds)) {
            row.preds.forEach(p => { if (p.confidence !== undefined && p.confidence !== null) confs.push(p.confidence); });
        }
        if (Array.isArray(row.species)) {
            row.species.forEach(s => { if (s.confidence !== undefined && s.confidence !== null) confs.push(s.confidence); });
        }
        return confs.map(c => safeNumber(c));
    }

    function extractCountsObject(row) {
        // If backend supplied counts object mapping organism->count
        if (row.counts && typeof row.counts === 'object' && !Array.isArray(row.counts)) return row.counts;
        return null;
    }

    function extractOrganismNames(row) {
        const names = [];
        if (row.organism && typeof row.organism === 'string') names.push(row.organism);
        if (Array.isArray(row.species)) {
            row.species.forEach(s => { if (s.name) names.push(s.name); });
        }
        if (Array.isArray(row.detections)) {
            row.detections.forEach(d => {
                if (d.organism) names.push(d.organism);
                else if (d.class_name) names.push(d.class_name);
                else if (d.name) names.push(d.name);
            });
        }
        // Normalize empty
        return names.length > 0 ? names : ['Unknown'];
    }

    // Update statistics cards
    function updateStats(metrics) {
        const totalEl = document.getElementById('total-analyses');
        const avgEl = document.getElementById('conf-avg');
        const highEl = document.getElementById('conf-high');
        const lowEl = document.getElementById('conf-low');

        if (totalEl) totalEl.textContent = metrics.total;
        if (avgEl) avgEl.textContent = Number.isNaN(metrics.avg) ? 'NaN' : metrics.avg.toFixed(2);
        if (highEl) highEl.textContent = metrics.high !== undefined ? metrics.high.toFixed(2) : '0';
        if (lowEl) lowEl.textContent = metrics.low !== undefined ? metrics.low.toFixed(2) : '0';
    }

    function updateSafeUnsafe(metrics) {
        const safeEl = document.getElementById('safe-count');
        const unsafeEl = document.getElementById('unsafe-count');
        if (safeEl) safeEl.textContent = metrics.safe || 0;
        if (unsafeEl) unsafeEl.textContent = metrics.unsafe || 0;
    }

    function updateMostDetected(metrics) {
        const el = document.getElementById('most-detected');
        if (!el) return;
        const counts = metrics.organismCounts || {};
        const names = Object.keys(counts);
        if (names.length === 0) {
            el.textContent = '—';
            return;
        }
        // Find max
        let max = -Infinity, winner = '—';
        names.forEach(n => {
            const v = Number(counts[n]) || 0;
            if (v > max) {
                max = v;
                winner = n;
            }
        });
        el.textContent = winner;
    }

    function updateRecentActivity(rows) {
        const recentEl = document.getElementById('recent-activity');
        if (!recentEl) return;
        recentEl.innerHTML = '';

        if (!rows || rows.length === 0) {
            recentEl.innerHTML = '<li style="padding:6px 0; opacity:0.6">No detections available</li>';
            return;
        }

        const recent = rows.slice(0, 5);
        recent.forEach(r => {
            const ts = parseTimestamp(r);
            const timeStr = ts ? new Date(ts).toLocaleString() : 'N/A';
            const name = (r.organism && String(r.organism)) || (r.summary && String(r.summary)) || 'Unknown';
            const conf = (r.confidence !== undefined && r.confidence !== null) ? Number(r.confidence).toFixed(2) : '0.00';
            const verdict = (r.verdict || (r.overall_verdict && r.overall_verdict.verdict) || 'Unknown');

            const li = document.createElement('li');
            li.style.padding = '6px 0';
            li.style.borderBottom = '1px solid #eee';
            li.innerHTML = `<div style="font-weight:700;color:#233">${escapeHtml(String(name))}</div><div style="font-size:12px;color:#666">${escapeHtml(String(verdict))} • Conf: ${conf} • ${timeStr}</div>`;
            recentEl.appendChild(li);
        });
    }

    function updateImageGrid(rows) {
        const container = document.getElementById('historyList');
        if (!container) return;
        if (!rows || rows.length === 0) {
            container.innerHTML = '<div style="padding: 40px; text-align: center; background: #f9f9f9; border-radius: 8px; color: #999;"><p>No history found. <a href="upload.html" style="color: #1F6FEB; font-weight: bold;">Upload an image</a> to get started.</p></div>';
            return;
        }

        // Build grid
        const gridItems = rows.map(row => buildCardHtml(row)).join('');
        container.innerHTML = `<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:16px">${gridItems}</div>`;
    }

    function buildCardHtml(item) {
        const id = item.id || item.analysis_id || item._id || '';
        const imageUrl = item.image_url || item.img || item.image || '';
        const ts = parseTimestamp(item);
        const timeStr = ts ? new Date(ts).toLocaleString() : 'N/A';

        // Organism names (may be multiple)
        const organismNames = extractOrganismNames(item);
        const organismsHtml = organismNames.map(n => `<span style="display:inline-block;background:#f1f5f9;padding:4px 8px;border-radius:999px;margin-right:6px;font-size:12px;color:#233">${escapeHtml(n)}</span>`).join('');

        // Confidence display: use item.confidence if present else compute average from detections
        let confVal = '0.00';
        const confs = extractConfidences(item);
        if (confs.length > 0) {
            const avg = confs.reduce((a,b)=>a+b,0)/confs.length;
            confVal = avg.toFixed(2);
        } else if (item.confidence !== undefined && item.confidence !== null) {
            confVal = safeNumber(item.confidence).toFixed(2);
        }

        const verdict = (item.verdict || (item.overall_verdict && item.overall_verdict.verdict) || 'Unknown');

        const imgHtml = imageUrl ? `<img src="${escapeAttr(imageUrl)}" alt="analysis" style="width:100%; height:150px; object-fit:cover; border-radius:6px; margin-bottom:10px">` : `<div style="width:100%; height:150px; background:#e9eef7; border-radius:6px; display:flex; align-items:center; justify-content:center; color:#9aa; margin-bottom:10px">No image</div>`;

        return `
            <div onclick="viewHistoryAnalysis('${escapeAttr(id)}')" style="background:white;padding:14px;border-radius:8px;cursor:pointer;border:1px solid #eef2ff;box-shadow:0 2px 6px rgba(8,30,70,0.04);transition:transform .18s;">
                ${imgHtml}
                <div style="font-size:12px;color:#999;margin-bottom:6px">${escapeHtml(timeStr)}</div>
                <div style="font-size:14px;font-weight:700;color:#123;margin-bottom:8px">${organismsHtml}</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px">Verdict: <strong>${escapeHtml(String(verdict))}</strong></div>
                <div style="font-size:13px;color:#444">Confidence: <strong>${confVal}</strong></div>
            </div>
        `;
    }

    // Helper: escape HTML to avoid injection when rendering backend strings
    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function escapeAttr(s) { return String(s).replace(/"/g, '&quot;'); }

    function renderEmptyState() {
        // Hide all analytics sections
        const statsSection = document.getElementById('stats-section');
        if (statsSection) statsSection.style.display = 'none';
        const chartsSection = document.getElementById('charts-section');
        if (chartsSection) chartsSection.style.display = 'none';
        const confSection = document.getElementById('confidence-section');
        if (confSection) confSection.style.display = 'none';
        const recentSection = document.getElementById('recent-section');
        if (recentSection) recentSection.style.display = 'none';

        // Empty grid message
        const container = document.getElementById('historyList');
        if (container) container.innerHTML = '<div style="padding: 40px; text-align: center; background: #f9f9f9; border-radius: 8px; color: #999;"><p>No history found. <a href="upload.html" style="color: #1F6FEB; font-weight: bold;">Upload an image</a> to get started.</p></div>';

        // recent activity
        const recent = document.getElementById('recent-activity');
        if (recent) recent.innerHTML = '<li style="padding:6px 0; opacity:0.6">No detections available</li>';

        // set stats defaults per requirements
        const totalEl = document.getElementById('total-analyses'); if (totalEl) totalEl.textContent = '0';
        const safeEl = document.getElementById('safe-count'); if (safeEl) safeEl.textContent = '0';
        const unsafeEl = document.getElementById('unsafe-count'); if (unsafeEl) unsafeEl.textContent = '0';
        const mostEl = document.getElementById('most-detected'); if (mostEl) mostEl.textContent = '—';
        const avgEl = document.getElementById('conf-avg'); if (avgEl) avgEl.textContent = 'NaN';
        const highEl = document.getElementById('conf-high'); if (highEl) highEl.textContent = '0';
        const lowEl = document.getElementById('conf-low'); if (lowEl) lowEl.textContent = '0';
    }

    // Expose click handler used by cards
    window.viewHistoryAnalysis = function(id) {
        try {
            localStorage.setItem('selected_history_id', id);
            // when going to analytics, let analytics page know this is a user selected id
            localStorage.setItem('selected_from_history', '1');
            window.location.href = 'analytics.html';
        } catch (e) { console.error(e); }
    };

})();
/**
 * history.js - Fetch and display past analyses
 * Clicking an item saves its ID and opens analytics.html
 */

(function() {
    document.addEventListener('DOMContentLoaded', function() {
        loadHistoryPage();
    });

    // Helper: Calculate analytics metrics from history rows
    function calculateAnalytics(rows) {
        const metrics = {
            total: rows.length,
            safe: 0,
            unsafe: 0,
            organisms: {},
            confidences: [],
            recent: []
        };

        rows.forEach(r => {
            // Count safe/unsafe based on summary or quality field
            const summary = (r.summary || '').toLowerCase();
            const quality = (r.quality || '').toLowerCase();
            const status = summary || quality;
            
            if (status.includes('safe') || status.includes('good')) metrics.safe++;
            else if (status.includes('unsafe') || status.includes('contaminated') || status.includes('harmful')) metrics.unsafe++;

            // Collect organism detections from preds or counts
            if (r.preds && Array.isArray(r.preds)) {
                r.preds.forEach(p => {
                    const name = p.class_name || p.name || 'Unknown';
                    metrics.organisms[name] = (metrics.organisms[name] || 0) + 1;
                });
            } else if (r.counts && typeof r.counts === 'object') {
                Object.entries(r.counts).forEach(([org, count]) => {
                    metrics.organisms[org] = (metrics.organisms[org] || 0) + count;
                });
            }

            // Collect confidence scores
            if (r.confidence !== undefined && r.confidence !== null) {
                metrics.confidences.push(r.confidence);
            } else if (r.preds && Array.isArray(r.preds)) {
                r.preds.forEach(p => {
                    if (p.confidence !== undefined) metrics.confidences.push(p.confidence);
                });
            }

            // Store for recent activity
            metrics.recent.push({
                timestamp: r.created_at || r.timestamp,
                filename: r.image_name || r.filename || 'Unknown',
                summary: r.summary || 'Analysis',
                total: r.preds ? r.preds.length : 0
            });
        });

        // Calculate confidence stats
        if (metrics.confidences.length > 0) {
            const avg = metrics.confidences.reduce((a, b) => a + b, 0) / metrics.confidences.length;
            metrics.confAvg = avg.toFixed(2);
            metrics.confHigh = Math.max(...metrics.confidences).toFixed(2);
            metrics.confLow = Math.min(...metrics.confidences).toFixed(2);
        }

        return metrics;
    }

    // Helper: Find most detected organism
    function getMostDetected(organisms) {
        if (Object.keys(organisms).length === 0) return '—';
        return Object.entries(organisms).reduce((a, b) => b[1] > a[1] ? b : a)[0];
    }

    // Helper: Draw bar chart for organisms
    function drawBarChart(canvas, organisms) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const names = Object.keys(organisms);
        const counts = Object.values(organisms);

        if (names.length === 0) {
            ctx.fillStyle = '#999';
            ctx.font = '14px Arial';
            ctx.fillText('No data', 20, 100);
            return;
        }

        const barWidth = canvas.width / (names.length * 1.5);
        const maxCount = Math.max(...counts, 1);
        const scale = (canvas.height * 0.8) / maxCount;

        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);

        const colors = ['#1F6FEB', '#10b981', '#f59e0b', '#ef4444'];

        names.forEach((name, idx) => {
            const x = idx * canvas.width / names.length + 20;
            const height = counts[idx] * scale;
            const y = canvas.height - height - 20;

            // Bar
            ctx.fillStyle = colors[idx % colors.length];
            ctx.fillRect(x, y, barWidth * 0.8, height);

            // Label
            ctx.fillStyle = '#333';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(name, x + barWidth * 0.4, canvas.height - 5);
            ctx.fillText(counts[idx], x + barWidth * 0.4, y - 5);
        });
    }

    // Helper: Draw pie chart for verdict distribution
    function drawPieChart(canvas, safe, unsafe) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const total = safe + unsafe;

        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);

        if (total === 0) {
            ctx.fillStyle = '#999';
            ctx.font = '14px Arial';
            ctx.fillText('No data', 50, 100);
            return;
        }

        const centerX = canvas.width * 0.4;
        const centerY = canvas.height * 0.5;
        const radius = 50;

        // Safe slice (green)
        const safeAngle = (safe / total) * 2 * Math.PI;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, 0, safeAngle);
        ctx.closePath();
        ctx.fillStyle = '#10b981';
        ctx.fill();

        // Unsafe slice (red)
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, safeAngle, 2 * Math.PI);
        ctx.closePath();
        ctx.fillStyle = '#ef4444';
        ctx.fill();

        // Legend
        ctx.font = '12px Arial';
        ctx.fillStyle = '#10b981';
        ctx.fillRect(canvas.width - 120, 10, 12, 12);
        ctx.fillStyle = '#333';
        ctx.fillText(`Safe: ${safe}`, canvas.width - 100, 20);

        ctx.fillStyle = '#ef4444';
        ctx.fillRect(canvas.width - 120, 30, 12, 12);
        ctx.fillStyle = '#333';
        ctx.fillText(`Unsafe: ${unsafe}`, canvas.width - 100, 40);
    }

    // Helper: Render analytics UI
    function renderAnalytics(rows) {
        const section = document.getElementById('analytics-section');
        if (!section) return;

        if (rows.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';
        const metrics = calculateAnalytics(rows);

        // Update cards
        document.getElementById('total-analyses').textContent = metrics.total;
        document.getElementById('safe-count').textContent = metrics.safe;
        document.getElementById('unsafe-count').textContent = metrics.unsafe;
        document.getElementById('most-detected').textContent = getMostDetected(metrics.organisms);

        // Update confidence summary
        document.getElementById('conf-avg').textContent = metrics.confAvg || '—';
        document.getElementById('conf-high').textContent = metrics.confHigh || '—';
        document.getElementById('conf-low').textContent = metrics.confLow || '—';

        // Draw charts
        drawBarChart(document.getElementById('bar-chart'), metrics.organisms);
        drawPieChart(document.getElementById('pie-chart'), metrics.safe, metrics.unsafe);

        // Recent activity (last 5)
        const recentList = document.getElementById('recent-activity');
        recentList.innerHTML = '';
        metrics.recent.slice(-5).reverse().forEach(r => {
            const li = document.createElement('li');
            li.style.cssText = 'padding:6px 0; border-bottom:1px solid #e0e0e0; opacity:0.9';
            li.innerHTML = `<strong>${r.filename}</strong> • ${r.summary} • ${r.total} detections<br><small style="opacity:0.6">${new Date(r.timestamp).toLocaleString()}</small>`;
            recentList.appendChild(li);
        });
    }

    /**
     * Load history from /api/history endpoint
     */
    async function loadHistoryPage() {
        const historyContainer = document.querySelector('.history-list');
        
        if (!historyContainer) {
            console.warn('history-list container not found');
            return;
        }

        try {
            // Show loading
            historyContainer.innerHTML = '<p style="text-align: center; color: #999;">Loading history...</p>';

            // Fetch history using centralized API client
            const historyData = await ApiClient.getHistory(100);
            
            if (!historyData || historyData.length === 0) {
                document.getElementById('analytics-section').style.display = 'none';
                historyContainer.innerHTML = `
                    <div style="padding: 40px; text-align: center; background: #f9f9f9; border-radius: 8px; color: #999;">
                        <p>No history found. <a href="upload.html" style="color: #1F6FEB; font-weight: bold;">Upload an image</a> to get started.</p>
                    </div>
                `;
                return;
            }

            // Render analytics with current data
            renderAnalytics(historyData);

            // Sort by date (newest first)
            const sorted = historyData.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            // Build grid of history items
            let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">';

            sorted.forEach(item => {
                const predCount = item.preds ? item.preds.length : 0;
                const imageUrl = item.image_url || '';
                const summary = item.summary || 'Analysis Result';

                html += `
                    <div onclick="viewHistoryAnalysis('${item.id}')" style="
                        padding: 16px;
                        background: white;
                        border-radius: 8px;
                        cursor: pointer;
                        transition: all 0.3s;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        border-left: 4px solid #1F6FEB;
                    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'">
                        ${imageUrl ? `<img src="${imageUrl}" alt="Analysis" style="width: 100%; height: 150px; object-fit: cover; border-radius: 4px; margin-bottom: 12px;">` : '<div style="width: 100%; height: 150px; background: #e0e0e0; border-radius: 4px; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; color: #999;">No image</div>'}
                        <p style="font-size: 12px; color: #999; margin: 0 0 8px 0;">${formatDate(item.created_at)}</p>
                        <p style="font-size: 14px; font-weight: 600; color: #2C3E50; margin: 0 0 8px 0; line-height: 1.4;">${summary}</p>
                        <p style="font-size: 12px; color: #1F6FEB; margin: 0;"><strong>${predCount}</strong> organisms detected</p>
                    </div>
                `;
            });

            html += '</div>';
            historyContainer.innerHTML = html;

        } catch (error) {
            historyContainer.innerHTML = `
                <div style="padding: 20px; background: #FEE; border-radius: 8px; color: #C33; border-left: 4px solid #C33;">
                    <strong>Error loading history:</strong> ${error.message}
                </div>
            `;
        }
    }

    /**
     * View a specific history item
     * Saves ID to localStorage and opens analytics.html
     */
    window.viewHistoryAnalysis = function(id) {
        try {
            // Save the selected history ID
            localStorage.setItem('selected_history_id', id);

            // Redirect to analytics.html
            window.location.href = 'analytics.html';
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    };

    /**
     * Format date string
     */
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (e) {
            return dateString;
        }
    }
})();

async function loadHistoryAnalytics() {
    try {
        const res = await fetch("http://127.0.0.1:8000/history_latest");
        const data = await res.json();

        // 1. Detections by Organism (Bar Chart)
        if (data.organism_counts && Object.keys(data.organism_counts).length > 0) {
            const ctx = document.getElementById("historyOrganismChart");
            if (ctx && !ctx.Chart) {
                new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: Object.keys(data.organism_counts),
                        datasets: [{
                            data: Object.values(data.organism_counts),
                            label: "Count"
                        }]
                    }
                });
            }
        }

        // 2. Verdict Distribution (Show Cropped Images)
        const container = document.getElementById("verdictImages");
        if (container && data.crops && data.crops.length > 0) {
            data.crops.forEach(src => {
                let img = document.createElement("img");
                img.src = src;
                img.style.width = "120px";
                img.style.borderRadius = "8px";
                img.style.border = "2px solid #ccc";
                container.appendChild(img);
            });
        }

    } catch (err) {
        console.log("Error loading history data:", err);
    }
}

window.addEventListener('load', loadHistoryAnalytics);
