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
     */
    function displayCurrentAnalysis() {
        const analysisJson = localStorage.getItem('current_analysis');
        
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

            // Build current analysis section
            const html = `
                <div style="margin-bottom: 40px;">
                    <h2 style="color: #2C3E50; margin-top: 0;">Current Analysis</h2>
                    
                    <!-- Summary -->
                    <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <h3 style="margin-top: 0; color: #2C3E50;">Summary</h3>
                        <p style="margin: 0; color: #666; font-size: 16px;">${analysis.summary || 'No summary available'}</p>
                    </div>

                    <!-- Metadata -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
                        <div style="padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #1F6FEB; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <p style="font-size: 12px; color: #999; margin: 0 0 8px 0; text-transform: uppercase;">Total Count</p>
                            <p style="font-size: 28px; font-weight: 700; color: #1F6FEB; margin: 0;">${analysis.preds ? analysis.preds.length : 0}</p>
                        </div>
                        <div style="padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #27AE60; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <p style="font-size: 12px; color: #999; margin: 0 0 8px 0; text-transform: uppercase;">Analysis ID</p>
                            <p style="font-size: 14px; font-weight: 600; color: #27AE60; margin: 0; word-break: break-all;">${analysis.id || 'N/A'}</p>
                        </div>
                        <div style="padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #E67E22; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <p style="font-size: 12px; color: #999; margin: 0 0 8px 0; text-transform: uppercase;">Created</p>
                            <p style="font-size: 14px; font-weight: 600; color: #E67E22; margin: 0;">${formatDate(analysis.created_at)}</p>
                        </div>
                    </div>

                    <!-- Species Table -->
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <h3 style="margin-top: 0; color: #2C3E50;">Species List</h3>
                        ${buildSpeciesTable(analysis.preds)}
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
     * Show message when no current analysis
     */
    function showNoCurrentAnalysis() {
        const analyticsSection = document.querySelector('.stats');
        if (analyticsSection) {
            analyticsSection.innerHTML = `
                <div style="padding: 40px; background: #F0F0F0; border-radius: 8px; text-align: center; color: #666;">
                    <p>No current analysis. Please <a href="upload.html" style="color: #1F6FEB; font-weight: bold;">upload an image</a> to analyze.</p>
                </div>
            `;
        }
    }

    /**
     * Build species table from predictions
     */
    function buildSpeciesTable(preds) {
        if (!preds || preds.length === 0) {
            return '<p style="color: #999;">No species data available.</p>';
        }

        // Group by class and count
        const speciesCounts = {};
        preds.forEach(pred => {
            const speciesClass = pred.class || 'Unknown';
            speciesCounts[speciesClass] = (speciesCounts[speciesClass] || 0) + 1;
        });

        let tableHtml = `
            <table style="width: 100%; border-collapse: collapse; margin-top: 12px;">
                <thead>
                    <tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">
                        <th style="padding: 12px; text-align: left; font-weight: 600; border: 1px solid #eee;">Species</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; border: 1px solid #eee;">Count</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; border: 1px solid #eee;">Confidence</th>
                    </tr>
                </thead>
                <tbody>
        `;

        Object.entries(speciesCounts)
            .sort((a, b) => b[1] - a[1])
            .forEach(([species, count]) => {
                // Get average confidence for this species
                const avgConfidence = getAverageConfidence(preds, species);
                tableHtml += `
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 12px; border: 1px solid #eee; font-weight: 600;">${species}</td>
                        <td style="padding: 12px; border: 1px solid #eee; text-align: center; color: #1F6FEB; font-weight: 700;">${count}</td>
                        <td style="padding: 12px; border: 1px solid #eee; text-align: center; color: #E67E22;">${(avgConfidence * 100).toFixed(1)}%</td>
                    </tr>
                `;
            });

        tableHtml += `</tbody></table>`;
        return tableHtml;
    }

    /**
     * Get average confidence for a species
     */
    function getAverageConfidence(preds, species) {
        const matching = preds.filter(p => p.class === species);
        if (matching.length === 0) return 0;
        
        const sum = matching.reduce((acc, p) => acc + (p.confidence || 0), 0);
        return sum / matching.length;
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
            localStorage.setItem('current_analysis', JSON.stringify(analysis));

            // Refresh the page to display
            location.reload();

        } catch (error) {
            alert(`Error loading analysis: ${error.message}`);
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
})();
