import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import cors from 'cors';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(cors());

// Serve output files
app.get('/outputs/:filename', (req, res) => {
  const filename = req.params.filename;
  const filepath = path.join(__dirname, '..', 'outputs', filename);
  
  // Security: prevent directory traversal
  const normalizedPath = path.normalize(filepath);
  const outputsDir = path.normalize(path.join(__dirname, '..', 'outputs'));
  
  if (!normalizedPath.startsWith(outputsDir)) {
    return res.status(403).json({ error: 'Access denied' });
  }
  
  fs.readFile(filepath, 'utf-8', (err, data) => {
    if (err) {
      return res.status(404).json({ error: 'File not found' });
    }
    try {
      res.json(JSON.parse(data));
    } catch (e) {
      res.status(400).json({ error: 'Invalid JSON' });
    }
  });
});

// List available output files
app.get('/api/outputs', (req, res) => {
  const outputsDir = path.join(__dirname, '..', 'outputs');
  fs.readdir(outputsDir, (err, files) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to read outputs directory' });
    }
    const jsonFiles = files
      .filter(f => f.endsWith('.json') && f.startsWith('requirements_'))
      .map(filename => {
        const filepath = path.join(outputsDir, filename);
        const stats = fs.statSync(filepath);
        return {
          filename,
          label: filename.replace('requirements_', '').replace('.json', ''),
          mtime: stats.mtime.getTime()
        };
      })
      .sort((a, b) => b.mtime - a.mtime);
    res.json(jsonFiles);
  });
});

app.listen(PORT, () => {
  console.log(`Output files server running on http://localhost:${PORT}`);
});
