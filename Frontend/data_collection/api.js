/**
 * API client for FastAPI backend
 * Handles HTTP requests and WebSocket connections
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_KEY = import.meta.env.VITE_API_KEY;

/**
 * Get WebSocket URL from API base URL
 */
export function getWebSocketUrl(path) {
  const wsUrl = API_BASE_URL.replace(/^http/, 'ws');
  return `${wsUrl}${path}`;
}

/**
 * Get API URL (for direct fetch calls)
 */
export function getApiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

/**
 * Get headers with optional API key
 */
function getHeaders() {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  return headers;
}

/**
 * Fetch wrapper with error handling
 */
async function fetchApi(path, options = {}) {
  const url = getApiUrl(path);
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * List available data files
 */
export async function listFiles() {
  return fetchApi('/files');
}

/**
 * Start a scraper job
 */
export async function startJob(params) {
  return fetchApi('/jobs/start', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * List all jobs
 */
export async function listJobs() {
  return fetchApi('/jobs');
}

/**
 * Get job status
 */
export async function getJobStatus(jobId) {
  return fetchApi(`/jobs/${jobId}`);
}

/**
 * Get job logs (persisted)
 */
export async function getJobLogs(jobId, tail = 200) {
  return fetchApi(`/jobs/${jobId}/logs?tail=${tail}`);
}

/**
 * Stop a running job
 */
export async function stopJob(jobId) {
  return fetchApi(`/jobs/${jobId}/stop`, {
    method: 'POST',
  });
}

/**
 * Download log file path (returns path, frontend can fetch it)
 */
export async function getLogDownloadPath(jobId) {
  return fetchApi(`/jobs/${jobId}/download`);
}

/**
 * Create WebSocket connection for live logs
 */
export function createLogWebSocket(jobId, onMessage, onError, onClose) {
  const wsUrl = getWebSocketUrl(`/ws/jobs/${jobId}`);
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log(`WebSocket connected for job ${jobId}`);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        onMessage(data.line);
      } else if (data.type === 'error') {
        onError(new Error(data.msg));
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError(error);
  };

  ws.onclose = () => {
    console.log(`WebSocket closed for job ${jobId}`);
    onClose();
  };

  return ws;
}

/**
 * List MongoDB collections
 */
export async function listCollections() {
  return fetchApi('/api/collections');
}

/**
 * Get paginated documents from a collection
 */
export async function getCollectionDocuments(collectionName, page = 1, limit = 50, searchQuery = null) {
  const params = new URLSearchParams({ page: page.toString(), limit: limit.toString() });
  if (searchQuery) {
    params.append('q', searchQuery);
  }
  return fetchApi(`/api/collections/${collectionName}?${params.toString()}`);
}

/**
 * Export collection as CSV
 */
export async function exportCollectionCSV(collectionName, searchQuery = null) {
  const params = new URLSearchParams();
  if (searchQuery) {
    params.append('q', searchQuery);
  }
  const url = getApiUrl(`/api/collections/${collectionName}/csv${params.toString() ? '?' + params.toString() : ''}`);
  const response = await fetch(url, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `${collectionName}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}

