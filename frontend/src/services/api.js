import axios from 'axios';

// When running Vite dev server (port 5173), target local port 8000.
// When accessed via Cloudflare Tunnel or production (port 8000), use relative path ''.
export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8000' : '')
).replace(/\/$/, '');

const client = axios.create({
  baseURL: API_BASE || undefined,
  timeout: 180000 // 3 minutes timeout for heavy satellite inference
});

export function resolveArtifactUrl(url) {
  if (!url) return null;

  // If accessed outside localhost:5173 (e.g. through Cloudflare Tunnel),
  // strip any hardcoded localhost/127.0.0.1 URLs returned by the backend so images load relatively.
  if (typeof window !== 'undefined' && window.location.port !== '5173') {
    if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\//i.test(url)) {
      return url.replace(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/, '');
    }
  }

  // Preserve absolute URLs (e.g. external links)
  if (/^https?:\/\//i.test(url)) return url;

  // Prefix relative URLs with API_BASE if set
  return (API_BASE ? API_BASE : '') + '/' + String(url).replace(/^\//, '');
}

export function normalizeApiError(error) {
  if (error?.code === 'ECONNABORTED') {
    return 'The analysis request timed out. The backend may still be processing; verify the job state before retrying.';
  }
  if (!error?.response) {
    return 'The GeoSentinel backend is unavailable. Check that FastAPI is running and try again.';
  }
  const detail = error.response.data?.detail;
  return typeof detail === 'string' ? detail : 'Backend request failed with HTTP ' + error.response.status + '.';
}

export async function checkBackendHealth() {
  const response = await client.get('/api/health', { timeout: 8000 });
  return response.data;
}

export async function executeChangeDetection({
  bbox,
  dates,
  threshold = 0.5,
  includeAgentSwarm = true,
  generateDossier = true
}) {
  const response = await client.post('/api/detect-change', {
    bbox,
    pre_start: dates.preStart,
    pre_end: dates.preEnd,
    post_start: dates.postStart,
    post_end: dates.postEnd,
    threshold,
    include_agent_swarm: includeAgentSwarm,
    generate_dossier: generateDossier,
  });
  return response.data;
}

export async function getJobStatus(jobId) {
  const response = await client.get(`/api/jobs/${jobId}`, { timeout: 15000 });
  return response.data;
}
