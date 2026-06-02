const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// Serve the static frontend
app.use(express.static(path.join(__dirname, 'public')));

// All routes serve the SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`\n  StockTime running at http://localhost:${PORT}\n`);
});
