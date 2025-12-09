import { useState, useEffect } from 'react';
import { listFiles, startJob } from '../api';

export default function FileList({ onJobStarted }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(null);

  useEffect(() => {
    loadFiles();
    // Refresh files every 30 seconds
    const interval = setInterval(loadFiles, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadFiles() {
    try {
      setError(null);
      const data = await listFiles();
      setFiles(data.files || []);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load files:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleStartAsync(fileName) {
    // Sanitize filename (basename only, no path traversal)
    const safeFileName = fileName.split('/').pop().split('\\').pop();
    
    setStarting(safeFileName);
    try {
      setError(null);
      const result = await startJob({
        script: 'async',
        file: safeFileName,
      });
      if (onJobStarted) {
        onJobStarted(result.job_id);
      }
    } catch (err) {
      setError(err.message);
      console.error('Failed to start job:', err);
    } finally {
      setStarting(null);
    }
  }

  async function handleStartBulk() {
    setStarting('bulk');
    try {
      setError(null);
      const result = await startJob({
        script: 'bulk',
        all: true,
      });
      if (onJobStarted) {
        onJobStarted(result.job_id);
      }
    } catch (err) {
      setError(err.message);
      console.error('Failed to start bulk job:', err);
    } finally {
      setStarting(null);
    }
  }

  if (loading) {
    return (
      <div className="panel-content">
        <div className="loading">Loading files...</div>
      </div>
    );
  }

  return (
    <div className="panel-content">
      {error && <div className="error-message">{error}</div>}
      
      <div style={{ marginBottom: '16px' }}>
        <button
          className="btn btn-primary"
          onClick={handleStartBulk}
          disabled={starting === 'bulk'}
          style={{ width: '100%' }}
        >
          {starting === 'bulk' ? 'Starting...' : 'Start Bulk Scraper'}
        </button>
      </div>

      {files.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📁</div>
          <div className="empty-state-text">No files found</div>
        </div>
      ) : (
        <ul className="file-list">
          {files.map((file) => (
            <li key={file} className="file-item">
              <span className="file-name" title={file}>
                {file}
              </span>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => handleStartAsync(file)}
                disabled={starting === file || starting !== null}
              >
                {starting === file ? '...' : 'Run'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

