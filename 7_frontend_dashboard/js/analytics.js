/**
 * analytics.js - Display current analysis and historical results
 * Section A: Current Analysis from localStorage
 * Section B: Historical Analytics from /api/history
 */

(function() {
    document.addEventListener('DOMContentLoaded', function() {
        // Load and display current analysis
        displayCurrentAnalysis();
        
        // Load and display history list
        loadHistoryList();
    });

    /**
     * A. Display Current Analysis from localStorage
     * NOTE: Large base64 images (annotated_image_base64, pie_chart_base64, bar_chart_base64)
     * are excluded from localStorage to prevent quota exceeded errors.
     * They are handled gracefully with fallback placeholders below.
     */
    function displayCurrentAnalysis() {
        // Prefer sessionStorage (set by upload.js) but fallback to legacy localStorage
        let analysisJson = sessionStorage.getItem('last_analysis') || localStorage.getItem('currentAnalysis') || localStorage.getItem('last_analysis');
        
        if (!analysisJson) {
            showNoCurrentAnalysis();
            return;
        }

        try {
            const analysis = JSON.parse(analysisJson);
            
            // Validate required fields
            if (!analysis) {
                showNoCurrentAnalysis();
                return;
            }

            // Extract data from backend response (supports new YOLO backend output)
            // totalDetections: prefer explicit field, else sum counts
            const totalDetections = analysis.total_detections || analysis.total_count || (analysis.count ? Object.values(analysis.count).reduce((a,b)=>a+Number(b),0) : 0);

            // perClass: if backend provided per_class, use it; otherwise build from count/max_confidence
            let perClass = analysis.per_class || [];
            if ((!perClass || perClass.length === 0) && analysis.count) {
                perClass = Object.keys(analysis.count).map(name => ({
                    class: name,
                    count: analysis.count[name],
                    percentage: totalDetections > 0 ? ((analysis.count[name] / totalDetections) * 100).toFixed(1) : 0,
                    avg_confidence: (analysis.max_confidence && analysis.max_confidence[name]) ? analysis.max_confidence[name] : (analysis.max_confidence ? Math.max(...Object.values(analysis.max_confidence)) : 0),
                    safety: 'Unknown',
                    description: ''
                }));
            }

            // Normalize perClass entries so analytics UI always finds the expected keys
            perClass = (perClass || []).map(item => {
                // item might come as {class_name, confidence, count} or legacy shapes
                const resolvedClass = item.class || item.class_name || item.name || item.label || 'undefined';
                const resolvedCount = (item.count !== undefined) ? item.count : (item.cnt !== undefined ? item.cnt : 0);
                const resolvedPercentage = (item.percentage !== undefined) ? item.percentage : (item.percent !== undefined ? item.percent : (totalDetections > 0 ? ((resolvedCount / totalDetections) * 100).toFixed(1) : 0));
                let resolvedAvgConf = null;
                if (item.avg_confidence !== undefined) resolvedAvgConf = item.avg_confidence;
                else if (item.avg_conf !== undefined) resolvedAvgConf = item.avg_conf;
                else if (item.confidence !== undefined) resolvedAvgConf = item.confidence;
                else if (analysis.max_confidence && analysis.max_confidence[resolvedClass] !== undefined) resolvedAvgConf = analysis.max_confidence[resolvedClass];
                else resolvedAvgConf = 'undefined';

                return {
                    class: String(resolvedClass),
                    count: Number(resolvedCount),
                    percentage: typeof resolvedPercentage === 'number' ? resolvedPercentage : String(resolvedPercentage),
                    avg_confidence: resolvedAvgConf,
                    safety: item.safety || 'Unknown',
                    description: item.description || ''
                };
            });

            // Overall verdict: prefer safety_status or overall_verdict
            const overallVerdict = (analysis.safety_status ? { verdict: analysis.safety_status, reason: '' } : (analysis.overall_verdict || { verdict: 'Unknown', reason: '' }));

            // Annotated image: backend returns base64 in image_with_boxes
            const annotatedImageUrl = analysis.annotated_image_url || '';
            const annotatedImageB64 = analysis.image_with_boxes || analysis.annotated_image_base64 || '';
            const pieChartB64 = analysis.pie_chart_base64 || '';
            const barChartB64 = analysis.bar_chart_base64 || '';

            // Store snapshot ID for PDF download
            window.currentSnapId = analysis.id || analysis.snap_id || analysis.analysis_id || null;

            // Safety verdict color
            const verdictColor = overallVerdict.verdict === 'Unsafe' ? '#FF6B6B' : 
                                 overallVerdict.verdict === 'Caution' ? '#FFA500' : '#27AE60';
            const verdictBgColor = overallVerdict.verdict === 'Unsafe' ? '#FFE5E5' : 
                                   overallVerdict.verdict === 'Caution' ? '#FFF3E0' : '#E8F8F5';

            const html = `
                <div style="margin-bottom: 40px;">
                    <h2 style="color: #2C3E50; margin-top: 0;">Water Quality Analysis Results</h2>
                    
                    <!-- Overall Safety Verdict (Prominent) -->
                    <div style="padding: 24px; background: ${verdictBgColor}; border-radius: 12px; border-left: 6px solid ${verdictColor}; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div>
                                <p style="margin: 0 0 8px 0; font-size: 12px; color: #999; text-transform: uppercase; font-weight: 600;">Overall Water Safety</p>
                                <p style="margin: 0; font-size: 32px; font-weight: 700; color: ${verdictColor};">${overallVerdict.verdict}</p>
                                <p style="margin: 8px 0 0 0; font-size: 14px; color: #555;">${overallVerdict.reason}</p>
                            </div>
                            <div style="text-align: center; font-size: 64px;">
                                ${overallVerdict.verdict === 'Unsafe' ? '⚠️' : overallVerdict.verdict === 'Caution' ? '⚡' : '✅'}
                            </div>
                        </div>
                    </div>

                    <!-- Summary -->
                    <div style="padding: 16px; background: #E8F4F8; border-radius: 8px; border-left: 4px solid #1F6FEB; margin-bottom: 20px;">
                        <p style="margin: 0; font-size: 16px; color: #2C3E50;"><strong>Detected ${totalDetections} microorganism${totalDetections !== 1 ? 's' : ''} across ${perClass.length} species.</strong></p>
                    </div>

                    <!-- Key Metrics -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 30px;">
                        <div style="padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #1F6FEB; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <p style="font-size: 12px; color: #999; margin: 0 0 8px 0; text-transform: uppercase;">Total Organisms</p>
                            <p style="font-size: 28px; font-weight: 700; color: #1F6FEB; margin: 0;">${totalDetections}</p>
                        </div>
                        <div style="padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #27AE60; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <p style="font-size: 12px; color: #999; margin: 0 0 8px 0; text-transform: uppercase;">Species Found</p>
                            <p style="font-size: 28px; font-weight: 700; color: #27AE60; margin: 0;">${perClass.length}</p>
                        </div>
                        <div style="padding: 16px; background: white; border-radius: 8px; border-left: 4px solid ${verdictColor}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <p style="font-size: 12px; color: #999; margin: 0 0 8px 0; text-transform: uppercase;">Safety Status</p>
                            <p style="font-size: 28px; font-weight: 700; color: ${verdictColor}; margin: 0;">${overallVerdict.verdict}</p>
                        </div>
                    </div>

                    <!-- Annotated Image with Bounding Boxes -->
                    ${annotatedImageUrl || annotatedImageB64 ? `
                        <div style="margin-bottom: 30px;">
                            <h3 style="color: #2C3E50; margin-top: 0;">Detected Organisms (with Bounding Boxes)</h3>
                            <img src="${annotatedImageUrl ? annotatedImageUrl : 'data:image/png;base64,' + annotatedImageB64}" alt="Annotated Detection" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 2px solid #1F6FEB;">
                        </div>
                    ` : ''}

                    <!-- Charts Section -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px;">
                        ${pieChartB64 ? `
                            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                <h3 style="margin-top: 0; color: #2C3E50;">Species Distribution (Pie Chart)</h3>
                                <img src="data:image/png;base64,${pieChartB64}" alt="Pie Chart" style="max-width: 100%; height: auto; border-radius: 4px;">
                            </div>
                        ` : ''}
                        ${barChartB64 ? `
                            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                                <h3 style="margin-top: 0; color: #2C3E50;">Species Count (Bar Chart)</h3>
                                <img src="data:image/png;base64,${barChartB64}" alt="Bar Chart" style="max-width: 100%; height: auto; border-radius: 4px;">
                            </div>
                        ` : ''}
                    </div>

                    <!-- Organism Details Table -->
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <h3 style="margin-top: 0; color: #2C3E50;">Detailed Organism Breakdown</h3>
                        ${buildOrganismTable(perClass)}
                    </div>
                </div>
            `;

            const analyticsSection = document.querySelector('.stats');
            if (analyticsSection) {
                analyticsSection.innerHTML = html;
            }

        } catch (error) {
            console.error('Error displaying current analysis:', error);
            showNoCurrentAnalysis();
        }
    }

    /**
     * Build detailed organism table with safety indicators
     */
    function buildOrganismTable(perClass) {
        if (!perClass || perClass.length === 0) {
            return '<p style="color: #999;">No organisms detected.</p>';
        }

        let tableHtml = `
            <table style="width: 100%; border-collapse: collapse; margin-top: 12px;">
                <thead>
                    <tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">
                        <th style="padding: 12px; text-align: left; font-weight: 600; border: 1px solid #eee;">Organism Name</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; border: 1px solid #eee;">Count</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; border: 1px solid #eee;">Percentage</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; border: 1px solid #eee;">Avg Confidence</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; border: 1px solid #eee;">Safety Level</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; border: 1px solid #eee;">Description</th>
                    </tr>
                </thead>
                <tbody>
        `;

        perClass.forEach((org, index) => {
            const safetyColor = org.safety === 'Unsafe' ? '#FF6B6B' : 
                               org.safety === 'Caution' ? '#FFA500' : '#27AE60';
            const safetyBg = org.safety === 'Unsafe' ? '#FFE5E5' : 
                            org.safety === 'Caution' ? '#FFF3E0' : '#E8F8F5';
            const bgColor = index % 2 === 0 ? '#ffffff' : '#f9f9f9';
            
            tableHtml += `
                <tr style="border-bottom: 1px solid #eee; background: ${bgColor};">
                    <td style="padding: 12px; border: 1px solid #eee; font-weight: 600; color: #2C3E50;">${org.class}</td>
                    <td style="padding: 12px; border: 1px solid #eee; text-align: center; color: #1F6FEB; font-weight: 700;">${org.count}</td>
                    <td style="padding: 12px; border: 1px solid #eee; text-align: center; color: #E67E22; font-weight: 600;">${org.percentage}%</td>
                    <td style="padding: 12px; border: 1px solid #eee; text-align: center; color: #666;">${org.avg_confidence}</td>
                    <td style="padding: 12px; border: 1px solid #eee; text-align: center;">
                        <span style="background: ${safetyBg}; color: ${safetyColor}; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 13px;">
                            ${org.safety}
                        </span>
                    </td>
                    <td style="padding: 12px; border: 1px solid #eee; color: #666; font-size: 13px;">${org.description}</td>
                </tr>
            `;
        });

        tableHtml += `</tbody></table>`;
        return tableHtml;
    }

    /**
     * Show message when no current analysis is available
     */
    function showNoCurrentAnalysis() {
        const analyticsSection = document.querySelector('.stats');
        if (analyticsSection) {
            analyticsSection.innerHTML = `
                <div style="padding: 40px; text-align: center; background: #F0F4F8; border-radius: 8px; border: 2px dashed #DDD;">
                    <p style="font-size: 18px; color: #999; margin: 0;">No current analysis available.</p>
                    <p style="font-size: 14px; color: #AAA; margin: 12px 0 0 0;">Please upload an image to get started.</p>
                    <a href="upload.html" class="btn primary" style="margin-top: 20px; display: inline-block; padding: 10px 20px; background: #1F6FEB; color: white; border-radius: 6px; text-decoration: none;">Upload Image</a>
                </div>
            `;
        }
    }

    /**
     * Format date string to readable format
     */
    function formatDate(dateString) {
        try {
            const date = new Date(dateString);
            const now = new Date();
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            
            const dateObj = new Date(date.getFullYear(), date.getMonth(), date.getDate());
            
            if (dateObj.getTime() === today.getTime()) {
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            } else if (dateObj.getTime() === yesterday.getTime()) {
                return 'Yesterday ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            } else {
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
            }
        } catch (e) {
            return dateString;
        }
    }

    /**
     * B. Load and display historical analyses
     */
    async function loadHistoryList() {
        try {
            const data = await ApiClient.getHistory(100);
            
            if (!data || data.length === 0) {
                // No history available
                return;
            }

            // Build history section
            let historyHtml = `
                <div style="margin-top: 40px; padding-top: 40px; border-top: 2px solid #eee;">
                    <h2 style="color: #2C3E50;">Historical Analytics</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px;">
            `;

            // Sort by date (newest first)
            const sorted = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            sorted.forEach(item => {
                const predCount = item.preds ? item.preds.length : 0;
                const imageUrl = item.image_url || '';

                historyHtml += `
                    <div onclick="loadHistoryAnalysis('${item.id}')" style="
                        padding: 12px;
                        background: white;
                        border-radius: 8px;
                        cursor: pointer;
                        transition: all 0.3s;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        border-left: 4px solid #1F6FEB;
                    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'">
                        ${imageUrl ? `<img src="${imageUrl}" alt="Analysis" style="width: 100%; height: 120px; object-fit: cover; border-radius: 4px; margin-bottom: 8px;">` : ''}
                        <p style="font-size: 12px; color: #999; margin: 0 0 4px 0;">${formatDate(item.created_at)}</p>
                        <p style="font-size: 14px; font-weight: 600; color: #2C3E50; margin: 0 0 4px 0;">${item.summary || 'Analysis'}</p>
                        <p style="font-size: 12px; color: #1F6FEB; margin: 0;"><strong>${predCount}</strong> organisms</p>
                    </div>
                `;
            });

            historyHtml += `
                    </div>
                </div>
            `;

            const analyticsSection = document.querySelector('.stats');
            if (analyticsSection) {
                // Append to existing content (don't replace)
                analyticsSection.innerHTML += historyHtml;
            }

        } catch (error) {
            console.error('Error loading history:', error);
            // Silently fail - history is optional
        }
    }

    /**
     * Load specific historical analysis
     * Called when clicking a history item
     */
    window.loadHistoryAnalysis = async function(id) {
        try {
            // Note: Backend /history endpoint returns all history
            // For now, fetch all and find by id, or update backend to support /history/{id}
            const allHistory = await ApiClient.getHistory(100);
            
            const analysis = allHistory.find(item => item.id === id);
            
            if (!analysis) {
                throw new Error('Analysis not found');
            }

            // Save to localStorage as current analysis
            localStorage.setItem('currentAnalysis', JSON.stringify(analysis));

            // Refresh the page to display
            location.reload();

        } catch (error) {
            alert(`Error loading analysis: ${error.message}`);
        }
    };

})();

/**
 * PDF Export: createPDFReport()
 * Reads visible DOM elements on analytics page (image, summary, counts, quality, timestamp)
 * and generates a PDF using html2canvas + jsPDF loaded dynamically.
 * Exposed as window.createPDFReport so existing button onclick handlers work unchanged.
 */
(function(){
    // Helper to load external script
    function loadScript(url){
        return new Promise((resolve, reject) => {
            // already loaded?
            if(document.querySelector(`script[src="${url}"]`)) return resolve();
            const s = document.createElement('script');
            s.src = url;
            s.onload = () => resolve();
            s.onerror = (e) => reject(new Error('Failed to load '+url));
            document.head.appendChild(s);
        });
    }

    async function ensureLibs(){
        // html2canvas and jspdf (UMD) CDNs
        const html2canvasUrl = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
        const jspdfUrl = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';

        const promises = [];
        if(typeof window.html2canvas === 'undefined') promises.push(loadScript(html2canvasUrl));
        if(typeof window.jspdf === 'undefined' && typeof window.jsPDF === 'undefined') promises.push(loadScript(jspdfUrl));
        await Promise.all(promises);
    }

    function findSummaryElement(container){
        // look for heading "Summary" then its following paragraph
        const headings = Array.from(container.querySelectorAll('h3'));
        for(const h of headings){
            if(/summary/i.test(h.textContent)){
                // next paragraph
                let p = h.nextElementSibling;
                while(p && p.tagName && p.tagName.toLowerCase() !== 'p') p = p.nextElementSibling;
                return p || null;
            }
        }
        // fallback: first paragraph
        return container.querySelector('p') || null;
    }

    function findValueByLabel(container, labelText){
        // look for element that contains labelText and return the sibling numeric/value element
        const elems = Array.from(container.querySelectorAll('*'));
        for(const el of elems){
            if(el.textContent && el.textContent.trim().toLowerCase().includes(labelText.toLowerCase())){
                // try next element
                let sibling = el.nextElementSibling;
                if(sibling) return sibling;
                // maybe parent contains value in a descendant
                const parent = el.parentElement;
                if(parent){
                    const strong = parent.querySelector('p,div,span');
                    if(strong && strong !== el) return strong;
                }
            }
        }
        return null;
    }

    async function createPDFReport(){
        try{
            await ensureLibs();

            const statsContainer = document.querySelector('.stats') || document.body;

            // Extract displayed elements
            const imgEl = statsContainer.querySelector('img');
            const summaryEl = findSummaryElement(statsContainer);

            // Attempt to find total count (look for 'Total Count' label)
            const totalEl = findValueByLabel(statsContainer, 'Total Count') || statsContainer.querySelector('.value') || null;

            // Attempt to find quality/contamination text (search for keywords)
            let qualityEl = null;
            const qualityLabels = ['quality','contamination','contamination level','water quality'];
            for(const lbl of qualityLabels){
                qualityEl = findValueByLabel(statsContainer, lbl);
                if(qualityEl) break;
            }

            // Attempt to find timestamp: look for 'Created' label or date-like content
            let timeEl = findValueByLabel(statsContainer, 'Created');
            if(!timeEl){
                // search for any element that looks like ISO date or contains ':' and '/'
                const candidates = Array.from(statsContainer.querySelectorAll('*')).filter(e=>/\d{4}-\d{2}-\d{2}/.test(e.textContent) || /:\d{2}/.test(e.textContent));
                timeEl = candidates.length ? candidates[0] : null;
            }

            // Compose a hidden container to render nicely
            const wrapper = document.createElement('div');
            wrapper.style.position = 'fixed';
            wrapper.style.left = '-9999px';
            wrapper.style.top = '0';
            wrapper.style.width = '800px';
            wrapper.style.padding = '20px';
            wrapper.style.background = '#fff';
            wrapper.style.boxSizing = 'border-box';

            const title = document.createElement('h2');
            title.textContent = 'AquaSafe AI - Analysis Report';
            title.style.fontFamily = 'Arial, sans-serif';
            wrapper.appendChild(title);

            if(timeEl) {
                const t = document.createElement('div');
                t.textContent = 'Timestamp: ' + timeEl.textContent.trim();
                t.style.marginBottom = '8px';
                wrapper.appendChild(t);
            }

            if(imgEl){
                const imgClone = document.createElement('img');
                imgClone.src = imgEl.src;
                imgClone.style.maxWidth = '100%';
                imgClone.style.display = 'block';
                imgClone.style.margin = '8px 0 12px 0';
                wrapper.appendChild(imgClone);
            }

            if(summaryEl){
                const sdiv = document.createElement('div');
                sdiv.innerHTML = '<h3 style="margin:8px 0 6px 0">Summary</h3>';
                const p = document.createElement('div');
                p.textContent = summaryEl.textContent.trim();
                sdiv.appendChild(p);
                wrapper.appendChild(sdiv);
            }

            const kv = document.createElement('div');
            kv.style.display = 'flex';
            kv.style.gap = '16px';
            kv.style.marginTop = '12px';

            const addKey = (label, el) => {
                const box = document.createElement('div');
                box.style.flex = '1';
                box.style.minWidth = '140px';
                box.style.padding = '8px';
                box.style.border = '1px solid #eee';
                const lab = document.createElement('div'); lab.style.fontSize='12px'; lab.style.color='#666'; lab.textContent = label;
                const val = document.createElement('div'); val.style.fontSize='18px'; val.style.fontWeight='700'; val.style.marginTop='6px';
                val.textContent = el ? el.textContent.trim() : '--';
                box.appendChild(lab); box.appendChild(val); kv.appendChild(box);
            };

            addKey('Total Count', totalEl);
            addKey('Contamination', qualityEl);
            wrapper.appendChild(kv);

            document.body.appendChild(wrapper);

            // Render to canvas and create PDF
            const canvas = await window.html2canvas(wrapper, {scale:2});
            // access jsPDF
            const { jsPDF } = window.jspdf || window.jspdf || window.jspdf || (window.jspdf ? window.jspdf : window);
            const pdf = (window.jspdf && window.jspdf.jsPDF) ? window.jspdf.jsPDF : (typeof window.jsPDF !== 'undefined' ? window.jsPDF : (jsPDF ? jsPDF : null));
            if(!pdf){
                throw new Error('jsPDF not available');
            }

            const imgData = canvas.toDataURL('image/jpeg', 0.95);
            const doc = new (pdf)("p","mm","a4");
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();

            // compute image dimensions preserving aspect ratio
            const imgProps = { width: canvas.width, height: canvas.height };
            const pxPerMm = canvas.width / (pageWidth * (96/25.4)); // approximate
            const imgWidthMm = pageWidth - 20; // margins
            const imgHeightMm = (canvas.height / canvas.width) * imgWidthMm;

            doc.addImage(imgData, 'JPEG', 10, 10, imgWidthMm, imgHeightMm);
            const fname = 'analysis_report_' + (new Date()).toISOString().replace(/[:.]/g,'-') + '.pdf';
            doc.save(fname);

            // cleanup
            document.body.removeChild(wrapper);

        }catch(err){
            console.error('createPDFReport error', err);
            alert('Could not create PDF: '+err.message);
        }
    }

    // expose globally
    window.createPDFReport = createPDFReport;
    
    // Handler for backend PDF report download
    window.downloadBackendPDF = function() {
        fetch("http://127.0.0.1:8000/generate-report")
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "report.pdf";
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            })
            .catch(err => console.error("PDF download failed:", err));
    };
})();

// --- PATCH: Show Annotated Image if backend provides bounding box output ---
document.addEventListener('DOMContentLoaded', function() {
    const analysisJson = localStorage.getItem('currentAnalysis');
    if (analysisJson) {
        try {
            const response = JSON.parse(analysisJson);
            if (response.annotated_image_url) {
                const annotatedImg = document.getElementById('annotatedImage');
                if (annotatedImg) {
                    annotatedImg.src = response.annotated_image_url;
                    annotatedImg.style.display = 'block';
                }
            }
        } catch (e) {
            console.error('Error showing annotated image:', e);
        }
    }
});

// --- PATCH: Fix organism names so they show correctly instead of "undefined" ---
(function() {
    const analysisJson = localStorage.getItem('currentAnalysis');
    if (analysisJson) {
        try {
            const response = JSON.parse(analysisJson);
            if (Array.isArray(response.organisms)) {
                response.organisms = response.organisms.map(org => ({
                    name: org.name || org.class || org.label || "Unknown",
                    count: org.count ?? 0,
                    confidence: org.confidence ?? 0,
                    safety: org.safety ?? "Unknown",
                    description: org.description ?? "Not available"
                }));
                localStorage.setItem('currentAnalysis', JSON.stringify(response));
            }
        } catch (e) {
            console.error('Error fixing organism names:', e);
        }
    }
})();

// --- Advanced Analytics Charts Loader ---
async function loadAnalyticsCharts() {
    try {
        const response = await fetch("http://127.0.0.1:8000/analytics-data");
        const data = await response.json();

        // Bar Chart Data - Organism Counts
        const organisms = Object.keys(data.organism_counts || {});
        const counts = Object.values(data.organism_counts || {});

        if (organisms.length > 0 && document.getElementById("speciesBarChart")) {
            new Chart(document.getElementById("speciesBarChart"), {
                type: "bar",
                data: {
                    labels: organisms,
                    datasets: [{
                        label: "Detected Count",
                        data: counts,
                        backgroundColor: "#0b6bd6"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true
                }
            });
        }

        // Pie Chart Data - Safety Status
        if (document.getElementById("safetyPieChart")) {
            new Chart(document.getElementById("safetyPieChart"), {
                type: "pie",
                data: {
                    labels: ["Safe", "Warning", "Dangerous"],
                    datasets: [{
                        data: [
                            data.safety?.safe || 0,
                            data.safety?.warning || 0,
                            data.safety?.dangerous || 0
                        ],
                        backgroundColor: ["#10b981", "#f59e0b", "#ef4444"]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true
                }
            });
        }

        // Line Chart - Detection Trend
        if (document.getElementById("trendLineChart")) {
            new Chart(document.getElementById("trendLineChart"), {
                type: "line",
                data: {
                    labels: data.trend?.dates || [],
                    datasets: [{
                        label: "Detections",
                        data: data.trend?.counts || [],
                        borderColor: "#0b6bd6",
                        backgroundColor: "rgba(11, 107, 214, 0.1)",
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true
                }
            });
        }

    } catch (error) {
        console.error("Error loading analytics charts:", error);
    }
}

// Load charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadAnalyticsCharts();
});
