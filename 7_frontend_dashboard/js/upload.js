/**
 * upload.js - Handle image upload and send to /api/predict
 * Shows loading modal while processing
 * Saves response to localStorage and redirects to analytics.html
 */

(function() {
    console.log('[upload.js] loaded');
    // Get DOM elements
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const preview = document.getElementById('preview');
    const previewImg = document.getElementById('previewImg');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const uploadArea = document.getElementById('uploadArea');
    const results = document.getElementById('results');

    let selectedFile = null;

    // Handle file selection
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        // Always update fileName display even if file type is not supported
        if (file) {
            selectedFile = file;
            fileName.textContent = file.name || 'Selected file';

            // Show preview (if browser can render the image type)
            const reader = new FileReader();
            reader.onload = function(event) {
                previewImg.src = event.target.result;
                preview.classList.add('show');
                // Show analyze button so user can proceed or see validation message
                analyzeBtn.style.display = 'block';
            };
            reader.readAsDataURL(file);

            // If the file is WebP, show a gentle notice (backend may prefer JPG/PNG)
            if (file.type === 'image/webp' || file.name.toLowerCase().endsWith('.webp')) {
                results.innerHTML = `
                    <div style="padding: 12px; background: #FFF7E6; border-radius: 6px; color: #995200; border-left: 4px solid #FFB74D; margin-top:8px;">
                        Note: WebP images may not be supported by the backend. For best results, convert to JPG/PNG before analyzing.
                    </div>
                `;
                results.classList.add('show');
            } else {
                // clear any prior notices
                results.innerHTML = '';
                results.classList.remove('show');
            }
        }
    });

    // Drag and drop functionality
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        fileInput.files = e.dataTransfer.files;
        fileInput.dispatchEvent(new Event('change'));
    });

    // Handle Analyze button click
    analyzeBtn.addEventListener('click', async function() {
        if (!selectedFile) {
            alert('Please select an image first');
            return;
        }

        // Validate file size (max 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (selectedFile.size > maxSize) {
            results.innerHTML = `
                <div style="padding: 20px; background: #FEE; border-radius: 8px; color: #C33; border-left: 4px solid #C33;">
                    <strong>Error:</strong> File size must be less than 10MB. Your file is ${(selectedFile.size / 1024 / 1024).toFixed(2)}MB.
                </div>
            `;
            results.classList.add('show');
            return;
        }

        // Validate file type
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        if (!validTypes.includes(selectedFile.type)) {
            results.innerHTML = `
                <div style="padding: 20px; background: #FEE; border-radius: 8px; color: #C33; border-left: 4px solid #C33;">
                    <strong>Error:</strong> Please upload a JPG or PNG image. You uploaded a ${selectedFile.type} file.
                </div>
            `;
            results.classList.add('show');
            return;
        }

        // Show loading modal
        showLoadingModal();

        try {
            // Use centralized API client to upload image
            const analysisData = await ApiClient.uploadImage(selectedFile);

            // Check for error in response
            if (analysisData.error) {
                hideLoadingModal();
                results.innerHTML = `
                    <div style="padding: 20px; background: #FEE; border-radius: 8px; color: #C33; border-left: 4px solid #C33;">
                        <strong>Error:</strong> ${analysisData.error}
                    </div>
                `;
                results.classList.add('show');
                return;
            }

            // Transform /predict response format to analytics.js format
            const transformedData = transformPredictResponse(analysisData);

            // --- SAFE STORAGE (prevents quota exceeded error) ---
            try {
                // Remove large base64 images from response before saving
                // Keep URLs (they're small strings) but exclude base64 (they're huge)
                const { annotated_image_base64, pie_chart_base64, bar_chart_base64, pdf_base64, ...safeData } = transformedData;

                // Save only text/small data to localStorage
                localStorage.setItem('currentAnalysis', JSON.stringify(safeData));
            } catch (storageError) {
                // If storage still fails, try removing even more data
                console.warn("Storage quota exceeded. Trying minimal data save.", storageError);
                try {
                    const { annotated_image_base64, pie_chart_base64, bar_chart_base64, pdf_base64, detections, per_class, ...minimalData } = transformedData;
                    localStorage.setItem('currentAnalysis', JSON.stringify(minimalData));
                } catch (finalError) {
                    console.error("Cannot save analysis data to localStorage.", finalError);
                    alert("Warning: Analysis data could not be saved. Results will show but won't persist on refresh.");
                }
            }

            // Hide loading modal
            hideLoadingModal();

            // Redirect to analytics.html
            setTimeout(() => {
                window.location.href = 'analytics.html';
            }, 500);

        } catch (error) {
            hideLoadingModal();
            
            // Show error message
            results.innerHTML = `
                <div style="padding: 20px; background: #FEE; border-radius: 8px; color: #C33; border-left: 4px solid #C33;">
                    <strong>Error:</strong> ${error.message}
                </div>
            `;
            results.classList.add('show');
        }
    });

    /**
     * Transform /predict response format to analytics.js expected format
     * /predict returns: { total_count, species, detections, counts, annotated_image_url, ... }
     * analytics.js expects: { total_detections, per_class, overall_verdict, annotated_image_url, ... }
     */
    function transformPredictResponse(predictResponse) {
        // Extract counts from either species array or counts object
        let counts = {};
        
        if (predictResponse.species && Array.isArray(predictResponse.species)) {
            // Convert species array to counts
            predictResponse.species.forEach(sp => {
                counts[sp.name] = sp.count;
            });
        } else if (predictResponse.counts) {
            counts = predictResponse.counts;
        }

        // Build per_class array for detailed breakdown
        const perClass = Object.entries(counts).map(([name, count]) => ({
            class_name: name,
            count: count,
            percentage: predictResponse.total_count > 0 
                ? ((count / predictResponse.total_count) * 100).toFixed(1)
                : 0
        }));

        // Determine safety verdict based on detections
        let verdict = 'Safe';
        let reason = 'No harmful organisms detected.';
        
        // Simple safety logic - customize based on your data
        const unsafeClasses = ['rotifer']; // Example: rotifers might be unsafe
        const cautionClasses = ['algae']; // Example: algae might be caution
        
        for (let className in counts) {
            if (unsafeClasses.includes(className.toLowerCase())) {
                verdict = 'Unsafe';
                reason = `High-risk organism(s) detected: ${className}. Immediate action recommended.`;
                break;
            } else if (cautionClasses.includes(className.toLowerCase())) {
                if (verdict !== 'Unsafe') {
                    verdict = 'Caution';
                    reason = `Presence of ${className} detected. Review recommended.`;
                }
            }
        }

        // Return transformed object
        return {
            total_detections: predictResponse.total_count || 0,
            per_class: perClass,
            overall_verdict: {
                verdict: verdict,
                reason: reason
            },
            annotated_image_url: predictResponse.annotated_image_url || '',
            timestamp: predictResponse.timestamp || new Date().toISOString(),
            analysis_id: predictResponse.analysis_id || predictResponse.id || 0,
            // Keep original fields for compatibility
            total_count: predictResponse.total_count || 0,
            species: predictResponse.species || [],
            counts: counts,
            detections: predictResponse.detections || [],
            uploaded_image_url: predictResponse.uploaded_image_url || ''
        };
    }
    });

    /**
     * Show loading modal with "Analyzing... Results will be shown soon."
     */
    function showLoadingModal() {
        let modal = document.getElementById('loadingModal');
        
        // Create modal if it doesn't exist
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'loadingModal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;
            
            modal.innerHTML = `
                <div style="
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    max-width: 400px;
                ">
                    <div style="
                        width: 50px;
                        height: 50px;
                        border: 4px solid #e0e0e0;
                        border-top-color: #1F6FEB;
                        border-radius: 50%;
                        margin: 0 auto 20px;
                        animation: spin 1s linear infinite;
                    "></div>
                    <h3 style="margin: 0 0 10px 0; color: #2C3E50;">Analyzing…</h3>
                    <p style="margin: 0; color: #666; font-size: 14px;">Results will be shown soon.</p>
                </div>
                <style>
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                </style>
            `;
            
            document.body.appendChild(modal);
        }
        
        modal.style.display = 'flex';
    }

    /**
     * Hide loading modal
     */
    function hideLoadingModal() {
        const modal = document.getElementById('loadingModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
})();
