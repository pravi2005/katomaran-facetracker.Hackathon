/**
 * Centralized API client for Katomaran Dashboard.
 */
const API_BASE = '';

async function fetchJson(endpoint) {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

async function postForm(endpoint, formData) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: formData,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(json.detail || `API error ${res.status}: ${res.statusText}`);
  }
  return json;
}

export const api = {
  getHealth: () => fetchJson('/api/health'),
  getStats: () => fetchJson('/api/stats'),
  getVisitors: () => fetchJson('/api/visitors'),
  getVisitorDetail: (faceId) => fetchJson(`/api/visitors/${faceId}`),
  getEvents: (limit = 100, eventType = '', faceId = '') => {
    let url = `/api/events?limit=${limit}`;
    if (eventType) url += `&event_type=${eventType}`;
    if (faceId) url += `&face_id=${faceId}`;
    return fetchJson(url);
  },
  getPresence: () => fetchJson('/api/presence'),
  getRegistrations: () => fetchJson('/api/registrations'),
  getAnalytics: () => fetchJson('/api/analytics'),
  getSystem: () => fetchJson('/api/system'),
  getLiveStatus: () => fetchJson('/api/live/status'),
  getImageUrl: (relPath) => relPath ? `${API_BASE}/api/images/${relPath}` : null,

  // Video analysis
  uploadAndAnalyze: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return postForm('/api/analyze', fd);
  },
  listAnalyses: () => fetchJson('/api/analyze'),
  getAnalysisStatus: (id) => fetchJson(`/api/analyze/${id}`),
  getAnalysisReport: (id) => fetchJson(`/api/analyze/${id}/report`),
};

