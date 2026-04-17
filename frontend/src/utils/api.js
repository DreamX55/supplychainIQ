/**
 * API utility for SupplyChainIQ backend
 */

const API_BASE = '/api/v1';

function getHeaders() {
  const userId = localStorage.getItem('supplychainiq_user_id') || 'guest';
  const preferred = localStorage.getItem('supplychainiq_preferred_provider') || '';
  const headers = {
    'Content-Type': 'application/json',
    'X-User-ID': userId,
  };
  if (preferred) headers['X-Preferred-Provider'] = preferred;
  return headers;
}

/**
 * Backend health (includes available providers)
 */
export async function getHealth() {
  const response = await fetch('/health');
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
}

/**
 * Store an encrypted API key for a provider in the user vault.
 */
export async function storeApiKey(provider, apiKey) {
  const response = await fetch(`${API_BASE}/keys/store`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || 'Failed to store API key');
  }
  return response.json();
}

/**
 * List providers the user has stored keys for + globally available providers.
 */
export async function listKeys() {
  const response = await fetch(`${API_BASE}/keys/list`, {
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to list keys');
  return response.json();
}

/**
 * Delete a stored key for a provider.
 */
export async function deleteApiKey(provider) {
  const response = await fetch(`${API_BASE}/keys/delete/${provider}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to delete key');
  return response.json();
}

/**
 * Upload context file
 */
export async function uploadContextFile(file, sessionId = null) {
  const formData = new FormData();
  formData.append('background_file', file);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  const userId = localStorage.getItem('supplychainiq_user_id') || 'guest';
  const preferred = localStorage.getItem('supplychainiq_preferred_provider') || '';
  const headers = { 'X-User-ID': userId };
  if (preferred) headers['X-Preferred-Provider'] = preferred;

  const response = await fetch(`${API_BASE}/analysis/upload-context`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    throw new Error('File upload failed');
  }

  return response.json();
}

/**
 * Analyze supply chain description
 */
export async function analyzeSupplyChain(description, sessionId = null, options = {}) {
  const body = {
    description,
    session_id: sessionId,
  };
  if (options.intraCountryFocus) {
    body.intra_country_focus = true;
    if (options.focusCountry) body.focus_country = options.focusCountry;
  }
  const response = await fetch(`${API_BASE}/analysis/analyze`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  });
  
  if (!response.ok) {
    throw new Error('Analysis failed');
  }
  
  return response.json();
}

/**
 * Send follow-up question
 */
export async function sendFollowUp(question, sessionId) {
  const response = await fetch(`${API_BASE}/analysis/followup`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      question,
      session_id: sessionId,
    }),
  });
  
  if (!response.ok) {
    throw new Error('Follow-up failed');
  }
  
  return response.json();
}

/**
 * Run a what-if scenario against an existing analysis.
 * scenario_type: 'supplier_switch' | 'route_change' | 'inventory_buffer'
 */
export async function runScenario(sessionId, scenarioType, parameters) {
  const response = await fetch(`${API_BASE}/analysis/scenario`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      session_id: sessionId,
      scenario_type: scenarioType,
      parameters: parameters || {},
    }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || 'Scenario simulation failed');
  }

  return response.json();
}

/**
 * Fetch demo personas (welcome-screen one-click presets).
 */
export async function getPersonas() {
  const response = await fetch(`${API_BASE}/analysis/personas`);
  if (!response.ok) throw new Error('Failed to fetch personas');
  return response.json();
}

/**
 * Fetch the live-looking risk intelligence alert feed.
 */
export async function getAlerts(limit = 8) {
  const response = await fetch(`${API_BASE}/analysis/alerts?limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch alerts');
  return response.json();
}

/**
 * Get user profile
 */
export async function getUserProfile() {
  const response = await fetch(`${API_BASE}/user/profile`, {
    headers: getHeaders(),
  });
  
  if (!response.ok) throw new Error('Failed to fetch profile');
  return response.json();
}

/**
 * Update user profile
 */
export async function updateUserProfile(companyName, companyType) {
  const response = await fetch(`${API_BASE}/user/profile`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify({
      company_name: companyName,
      company_type: companyType,
    }),
  });
  
  if (!response.ok) throw new Error('Failed to update profile');
  return response.json();
}

/**
 * Get user sessions (Intelligence Vault)
 */
export async function getUserSessions() {
  const response = await fetch(`${API_BASE}/user/sessions`, {
    headers: getHeaders(),
  });
  
  if (!response.ok) throw new Error('Failed to fetch sessions');
  return response.json();
}

/**
 * Get full session details
 */
export async function getSessionDetails(sessionId) {
  const response = await fetch(`${API_BASE}/analysis/session/${sessionId}`, {
    headers: getHeaders(),
  });
  
  if (!response.ok) throw new Error('Failed to fetch session details');
  return response.json();
}
