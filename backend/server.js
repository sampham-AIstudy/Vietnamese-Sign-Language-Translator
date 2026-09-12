/**
 * Node.js Express Backend for Vietnamese Sign Language (VSL) System.
 * - Serves VSL 4,362 vocabulary video dictionary with 3 regional dialects (North, Central, South)
 * - Manages real-time translation session history and logging
 * - Health-checks Python FastAPI AI Inference Service
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const morgan = require('morgan');

const app = express();
const PORT = process.env.PORT || 5000;
const PYTHON_AI_URL = process.env.PYTHON_AI_URL || 'http://localhost:8000';

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(morgan('dev'));

// In-memory cache for VSL labels
let vslDictionary = [];
const CSV_PATH = path.join(__dirname, '..', 'data (2)', 'Dataset', 'Labels', 'label.csv');
const VIDEOS_DIR = path.join(__dirname, '..', 'data (2)', 'Dataset', 'Videos');

// Load CSV into memory
function loadDictionary() {
  if (!fs.existsSync(CSV_PATH)) {
    console.warn(`[WARN] Label CSV not found at: ${CSV_PATH}`);
    return;
  }
  const results = [];
  fs.createReadStream(CSV_PATH)
    .pipe(csv())
    .on('data', (data) => {
      const vid = data.VIDEO || '';
      let region = 'Chung';
      let regionCode = 'All';
      if (vid.includes('B.mp4')) {
        region = 'Miền Bắc (North)';
        regionCode = 'B';
      } else if (vid.includes('T.mp4')) {
        region = 'Miền Trung (Central)';
        regionCode = 'T';
      } else if (vid.includes('N.mp4')) {
        region = 'Miền Nam (South)';
        regionCode = 'N';
      }

      results.push({
        id: data.ID || results.length + 1,
        video: vid,
        label: data.LABEL || '',
        region,
        regionCode,
      });
    })
    .on('end', () => {
      vslDictionary = results;
      console.log(`[INFO] Loaded ${vslDictionary.length} VSL vocabulary items into memory.`);
    })
    .on('error', (err) => {
      console.error('[ERROR] Failed reading label CSV:', err);
    });
}

loadDictionary();

// In-memory translation session history
const translationHistory = [];

// ==============================================================================
// ROUTES
// ==============================================================================

// 1. System Health & Microservices Status
app.get('/api/status', async (req, res) => {
  let aiStatus = 'offline';
  let aiDetails = null;

  try {
    const aiRes = await fetch(`${PYTHON_AI_URL}/health`);
    if (aiRes.ok) {
      aiStatus = 'online';
      aiDetails = await aiRes.json();
    }
  } catch (err) {
    aiStatus = 'unreachable';
  }

  res.json({
    node_server: 'online',
    timestamp: new Date().toISOString(),
    dictionary_items_loaded: vslDictionary.length,
    python_ai_engine: {
      status: aiStatus,
      url: PYTHON_AI_URL,
      details: aiDetails,
    },
  });
});

// 2. VSL Dictionary Search & Pagination
app.get('/api/dictionary', (req, res) => {
  const { q = '', region = '', page = 1, limit = 20 } = req.query;
  const p = Math.max(1, parseInt(page, 10));
  const lim = Math.min(100, Math.max(1, parseInt(limit, 10)));

  let filtered = vslDictionary;

  if (q.trim()) {
    const searchLower = q.toLowerCase().trim();
    filtered = filtered.filter((item) =>
      item.label.toLowerCase().includes(searchLower)
    );
  }

  if (region.trim() && region !== 'All') {
    const reg = region.toUpperCase().trim();
    filtered = filtered.filter((item) => item.regionCode === reg);
  }

  const total = filtered.length;
  const offset = (p - 1) * lim;
  const items = filtered.slice(offset, offset + lim);

  res.json({
    total,
    page: p,
    limit: lim,
    totalPages: Math.ceil(total / lim),
    items,
  });
});

// 3. Translation History
app.get('/api/history', (req, res) => {
  res.json({
    count: translationHistory.length,
    history: translationHistory.slice(-50).reverse(),
  });
});

app.post('/api/history', (req, res) => {
  const { text, confidence, words, duration_sec } = req.body;
  if (!text) {
    return res.status(400).json({ error: 'Text is required' });
  }

  const record = {
    id: Date.now().toString(),
    text,
    words: words || text.split(' '),
    confidence: confidence || 1.0,
    duration_sec: duration_sec || 0,
    createdAt: new Date().toISOString(),
  };

  translationHistory.push(record);
  if (translationHistory.length > 200) {
    translationHistory.shift();
  }

  res.status(201).json(record);
});

// 4. Serve video clips statically if exists
if (fs.existsSync(VIDEOS_DIR)) {
  app.use('/videos', express.static(VIDEOS_DIR));
}

app.listen(PORT, () => {
  console.log(`[READY] VSL Node.js Backend listening on http://localhost:${PORT}`);
  console.log(`[CONFIG] Connecting to Python AI Engine at: ${PYTHON_AI_URL}`);
});
