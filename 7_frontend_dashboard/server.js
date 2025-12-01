// Simple Express server to serve frontend at http://localhost:3000
// - Serves static files from the project directory
// - Enables CORS for convenience
// Usage: node server.js

const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS (frontend static server won't need it for backend requests
// since the backend has CORS enabled, but this is harmless)
app.use(cors());

// Serve static files from this directory (the frontend folder)
app.use(express.static(path.join(__dirname)));

// For any unknown route, serve index.html to allow navigation between pages
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Frontend server running at http://localhost:${PORT}`);
});
