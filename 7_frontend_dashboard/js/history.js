/**
 * history.js - Fetch and display past analyses
 * Clicking an item saves its ID and opens analytics.html
 */

(function() {
    document.addEventListener('DOMContentLoaded', function() {
        loadHistoryPage();
    });

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
                historyContainer.innerHTML = `
                    <div style="padding: 40px; text-align: center; background: #f9f9f9; border-radius: 8px; color: #999;">
                        <p>No history found. <a href="upload.html" style="color: #1F6FEB; font-weight: bold;">Upload an image</a> to get started.</p>
                    </div>
                `;
                return;
            }

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
