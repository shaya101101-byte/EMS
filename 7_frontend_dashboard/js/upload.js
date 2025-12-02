/**
 * upload.js - Handle image upload and send to /api/predict
 * Shows loading modal while processing
 * Saves response to localStorage and redirects to analytics.html
 */

(function() {
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
        if (file) {
            selectedFile = file;
            fileName.textContent = file.name;
            
            // Show preview
            const reader = new FileReader();
            reader.onload = function(event) {
                previewImg.src = event.target.result;
                preview.classList.add('show');
                analyzeBtn.style.display = 'block';
            };
            reader.readAsDataURL(file);
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

            // Save response to localStorage with the key "currentAnalysis"
            localStorage.setItem('currentAnalysis', JSON.stringify(analysisData));

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
