/**
 * API Client - Centralized backend communication
 * Base URL: http://localhost:8000
 * All requests go through this module for consistency
 */

const BASE_URL = 'http://127.0.0.1:8000';

const ApiClient = {
    /**
     * Upload image and run full analysis
     * POST /analyze-image
     * @param {File} file - Image file (JPG/PNG)
     * @returns {Promise} - Analysis result with organisms, charts, safety verdict, PDF
     */
    uploadImage: async function(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);  // Note: /analyze-image expects field named 'file'

            const response = await fetch(`${BASE_URL}/analyze-image`, {
                method: 'POST',
                body: formData,
                // NOTE: Do NOT set Content-Type header when using FormData
                // Browser will set it automatically with boundary
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    },

    /**
     * Get detection history
     * GET /history?limit=100
     * @param {number} limit - Maximum number of records (default 100)
     * @returns {Promise} - Array of past detections
     */
    getHistory: async function(limit = 100) {
        try {
            const response = await fetch(`${BASE_URL}/history?limit=${limit}`);

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();
            // Backend returns { history: [...] }, so extract the array
            return data.history || data;
        } catch (error) {
            console.error('History fetch error:', error);
            throw error;
        }
    },

    /**
     * Get statistics/analytics data
     * GET /stats?hours=48
     * @param {number} hours - Time range in hours (default 48)
     * @returns {Promise} - Timeseries stats data
     */
    getStats: async function(hours = 48) {
        try {
            const response = await fetch(`${BASE_URL}/stats?hours=${hours}`);

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Stats fetch error:', error);
            throw error;
        }
    },

    /**
     * Check backend health status
     * GET /status
     * @returns {Promise} - Status info
     */
    getStatus: async function() {
        try {
            const response = await fetch(`${BASE_URL}/status`);

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Status check error:', error);
            throw error;
        }
    },

    /**
     * Save analysis to history (if backend supports it)
     * POST /history/save
     * @param {File} imageFile - Original image file
     * @param {Object} analysisData - Analysis result from /predict
     * @returns {Promise} - Save confirmation
     */
    saveToHistory: async function(imageFile, analysisData) {
        try {
            const formData = new FormData();
            formData.append('image', imageFile);
            formData.append('analysis_json', JSON.stringify(analysisData));

            const response = await fetch(`${BASE_URL}/history/save`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Save to history error:', error);
            throw error;
        }
    },
};
