// static/admin/admin.js

// Store admin token in localStorage for client-side use
(function initializeAdmin() {
    const token = localStorage.getItem("admin_token");
    if (!token) {
        localStorage.setItem("admin_token", "ADMIN_TOKEN");
    }
})();

// Utility: Add auth header to all fetch requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const options = args[1] || {};
    if (!options.headers) options.headers = {};
    options.headers["x-admin-token"] = localStorage.getItem("admin_token") || "ADMIN_TOKEN";
    return originalFetch.apply(this, [args[0], options]);
};

// Auto-reload pages every 5 seconds if admin data exists
(function autoReload() {
    if (window.location.pathname.startsWith("/admin")) {
        // Pages will implement their own reload logic via setInterval
    }
})();

console.log("Admin dashboard initialized");
