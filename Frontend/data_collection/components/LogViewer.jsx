import { useState, useEffect, useRef } from 'react';
import { createLogWebSocket, getJobLogs, getLogDownloadPath, getApiUrl } from '../api';

export default function LogViewer({ jobId }) {
  const [lines, setLines] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef(null);
  const wsRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!jobId) {
      setLines([]);
      setWsConnected(false);
      setError(null);
      return;
    }

    // Load initial logs
    loadInitialLogs();

    // Connect WebSocket
    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, [jobId]);

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lines, autoScroll]);

  // Handle manual scroll
  function handleScroll() {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setAutoScroll(isNearBottom);
  }

  async function loadInitialLogs() {
    try {
      setError(null);
      const data = await getJobLogs(jobId, 200);
      setLines(data.log || []);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load logs:', err);
    }
  }

  function connectWebSocket() {
    if (!jobId) return;

    disconnectWebSocket();

    const ws = createLogWebSocket(
      jobId,
      (line) => {
        // Handle special control messages
        if (line.startsWith('__PROCESS_EXIT__:')) {
          const status = line.replace('__PROCESS_EXIT__:', '');
          setLines((prev) => [...prev, `\n[Process ${status}]`]);
          setWsConnected(false);
          return;
        }
        if (line.startsWith('__ERROR__:')) {
          const errMsg = line.replace('__ERROR__:', '');
          setError(errMsg);
          setLines((prev) => [...prev, `\n[Error: ${errMsg}]`]);
          return;
        }

        // Regular log line
        setLines((prev) => [...prev, line]);
      },
      (err) => {
        setError(err.message || 'WebSocket error');
        setWsConnected(false);
      },
      () => {
        setWsConnected(false);
      }
    );

    wsRef.current = ws;
    setWsConnected(true);
  }

  function disconnectWebSocket() {
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        // Ignore
      }
      wsRef.current = null;
    }
    setWsConnected(false);
  }

  async function handleDownload() {
    try {
      const data = await getLogDownloadPath(jobId);
      // The backend returns a path, but we need to fetch the actual file
      // Since the backend doesn't serve static files, we'll use the logs endpoint
      // For a full download, we can fetch with a large tail value
      const logData = await getJobLogs(jobId, 10000);
      const content = logData.log.join('\n');
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `job_${jobId.substring(0, 8)}.log`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
      console.error('Failed to download log:', err);
    }
  }

  if (!jobId) {
    return (
      <div className="log-viewer">
        <div className="panel-header">Log Viewer</div>
        <div className="panel-content">
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <div className="empty-state-text">Select a job to view logs</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="log-viewer">
      <div className="log-viewer-header">
        <span className="log-viewer-title">Job: {jobId.substring(0, 8)}</span>
        <div className="log-viewer-actions">
          <button className="btn btn-sm btn-secondary" onClick={loadInitialLogs}>
            Refresh Logs
          </button>
          <button className="btn btn-sm btn-secondary" onClick={handleDownload}>
            Download
          </button>
          {!wsConnected && (
            <button className="btn btn-sm btn-primary" onClick={connectWebSocket}>
              Reconnect
            </button>
          )}
        </div>
      </div>
      <div
        className="log-content"
        ref={containerRef}
        onScroll={handleScroll}
      >
        {lines.length === 0 ? (
          <div className="log-line empty">No logs available</div>
        ) : (
          lines.map((line, idx) => (
            <div key={idx} className="log-line">
              {line || ' '}
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
      <div className={`log-status ${error ? 'error' : wsConnected ? 'connected' : ''}`}>
        {error ? (
          <>Error: {error}</>
        ) : wsConnected ? (
          <>● Connected (live streaming)</>
        ) : (
          <>○ Disconnected</>
        )}
        {!autoScroll && (
          <span style={{ marginLeft: '12px', cursor: 'pointer' }} onClick={() => setAutoScroll(true)}>
            (Click to auto-scroll)
          </span>
        )}
      </div>
    </div>
  );
}

