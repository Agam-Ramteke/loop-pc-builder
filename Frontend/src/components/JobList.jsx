import { useState, useEffect } from 'react';
import { listJobs, stopJob } from '../api';

export default function JobList({ selectedJobId, onJobSelect, onJobStopped }) {
  const [jobs, setJobs] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stopping, setStopping] = useState(null);

  useEffect(() => {
    loadJobs();
    // Poll jobs every 2-3 seconds
    const interval = setInterval(loadJobs, 2500);
    return () => clearInterval(interval);
  }, []);

  async function loadJobs() {
    try {
      setError(null);
      const data = await listJobs();
      setJobs(data || {});
    } catch (err) {
      setError(err.message);
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleStop(jobId, e) {
    e.stopPropagation();
    setStopping(jobId);
    try {
      setError(null);
      await stopJob(jobId);
      if (onJobStopped) {
        onJobStopped(jobId);
      }
    } catch (err) {
      setError(err.message);
      console.error('Failed to stop job:', err);
    } finally {
      setStopping(null);
    }
  }

  function getStatusClass(status) {
    if (!status) return '';
    if (status.startsWith('running')) return 'running';
    if (status.startsWith('finished')) return 'finished';
    if (status.startsWith('failed')) return 'failed';
    if (status.startsWith('terminating')) return 'terminating';
    if (status.startsWith('queued')) return 'queued';
    return '';
  }

  function shortenJobId(jobId) {
    return jobId ? jobId.substring(0, 8) : 'unknown';
  }

  const jobEntries = Object.entries(jobs);

  if (loading && jobEntries.length === 0) {
    return (
      <div className="panel-content">
        <div className="loading">Loading jobs...</div>
      </div>
    );
  }

  return (
    <div className="panel-content">
      {error && <div className="error-message">{error}</div>}
      
      {jobEntries.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">⚙️</div>
          <div className="empty-state-text">No jobs running</div>
        </div>
      ) : (
        <ul className="job-list">
          {jobEntries.map(([jobId, job]) => (
            <li
              key={jobId}
              className={`job-item ${selectedJobId === jobId ? 'selected' : ''}`}
              onClick={() => onJobSelect && onJobSelect(jobId)}
            >
              <div className="job-header">
                <span className="job-id" title={jobId}>
                  {shortenJobId(jobId)}
                </span>
                <span className={`job-status ${getStatusClass(job.status)}`}>
                  {job.status || 'unknown'}
                </span>
              </div>
              {job.cmd && (
                <div className="job-info" title={job.cmd}>
                  {job.cmd.length > 50 ? `${job.cmd.substring(0, 50)}...` : job.cmd}
                </div>
              )}
              <div className="job-actions">
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={() => onJobSelect && onJobSelect(jobId)}
                >
                  View Logs
                </button>
                {job.status && job.status.startsWith('running') && (
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={(e) => handleStop(jobId, e)}
                    disabled={stopping === jobId}
                  >
                    {stopping === jobId ? 'Stopping...' : 'Stop'}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

