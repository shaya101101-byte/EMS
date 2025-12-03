/**
 * analytics_charts.js
 * Fetches analytics data from /analytics-data and renders Chart.js charts
 */

(function() {
    console.log('[analytics_charts.js] loaded');

    // Wait for Chart.js to be available
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded');
        return;
    }

    // Fetch analytics data from backend
    async function loadAnalyticsCharts() {
        try {
            const res = await fetch('http://127.0.0.1:8000/analytics-data', {
                headers: { 'Accept': 'application/json' }
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            // Render charts
            renderSpeciesBarChart(data.speciesCounts);
            renderSafetyPieChart(data.safetyStats);
            renderTrendLineChart(data.dailyTrend);

        } catch (error) {
            console.error('Error loading analytics data:', error);
            document.getElementById('charts-section').innerHTML += 
                `<p style="color: red; padding: 20px;">Failed to load analytics data.</p>`;
        }
    }

    function renderSpeciesBarChart(speciesCounts) {
        const ctx = document.getElementById('speciesBarChart');
        if (!ctx) return;

        const species = Object.keys(speciesCounts);
        const counts = Object.values(speciesCounts);

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: species.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
                datasets: [{
                    label: 'Organism Count',
                    data: counts,
                    backgroundColor: ['#1F6FEB', '#27AE60', '#E67E22', '#9B59B6'],
                    borderColor: ['#1560c0', '#22935f', '#d66e1a', '#8e4aa6'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, position: 'top' },
                    title: { display: true, text: 'Organism Detection by Species' }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Count' } }
                }
            }
        });
    }

    function renderSafetyPieChart(safetyStats) {
        const ctx = document.getElementById('safetyPieChart');
        if (!ctx) return;

        const labels = Object.keys(safetyStats).map(k => k.charAt(0).toUpperCase() + k.slice(1));
        const values = Object.values(safetyStats);
        const colors = ['#27AE60', '#FFA500', '#FF6B6B'];

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: ['#1e8449', '#e68900', '#e55a5a'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, position: 'bottom' },
                    title: { display: true, text: 'Water Safety Distribution' }
                }
            }
        });
    }

    function renderTrendLineChart(dailyTrend) {
        const ctx = document.getElementById('trendLineChart');
        if (!ctx) return;

        const dates = dailyTrend.map(d => d.date);
        const counts = dailyTrend.map(d => d.count);

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Daily Detection Count',
                    data: counts,
                    borderColor: '#1F6FEB',
                    backgroundColor: 'rgba(31, 111, 235, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, position: 'top' },
                    title: { display: true, text: 'Detection Trend Over Time' }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Count' } }
                }
            }
        });
    }

    // Load charts when DOM is ready
    document.addEventListener('DOMContentLoaded', loadAnalyticsCharts);

})();

// PDF Report Download
document.getElementById("downloadPdfBtn").addEventListener("click", () => {
    fetch("/analytics-report-pdf")
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "water_quality_report.pdf";
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(err => console.error("PDF download failed:", err));
});
