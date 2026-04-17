/**
 * API utility for SupplyChainIQ backend
 */

const API_BASE = '/api/v1';

function getHeaders() {
  const jwt = localStorage.getItem('supplychainiq_jwt');
  const userId = localStorage.getItem('supplychainiq_user_id') || 'guest';
  const preferred = localStorage.getItem('supplychainiq_preferred_provider') || '';
  const headers = {
    'Content-Type': 'application/json',
  };
  // Prefer JWT auth when available; fall back to legacy guest header
  // so the one-click demo path keeps working without registration.
  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  } else {
    headers['X-User-ID'] = userId;
  }
  if (preferred) headers['X-Preferred-Provider'] = preferred;
  return headers;
}

/**
 * Register a new account. On success, stores the JWT + user info in
 * localStorage and returns the user object.
 */
export async function register(email, password, companyName, companyType) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
      company_name: companyName || null,
      company_type: companyType || null,
    }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || 'Registration failed');
  }
  const data = await response.json();
  _persistAuth(data);
  return data;
}

/**
 * Login with email + password. On success, stores JWT and returns user info.
 */
export async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || 'Login failed');
  }
  const data = await response.json();
  _persistAuth(data);
  return data;
}

/**
 * Validate the stored JWT against the backend. Returns the user object
 * on success, or null on any failure (no token, expired, invalid).
 * Used on app boot to decide whether to show the login screen.
 */
export async function fetchCurrentUser() {
  const jwt = localStorage.getItem('supplychainiq_jwt');
  if (!jwt) return null;
  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: { 'Authorization': `Bearer ${jwt}` },
    });
    if (!response.ok) {
      // Token rejected — clear it so the user gets a clean login screen
      logout();
      return null;
    }
    return await response.json();
  } catch {
    return null;
  }
}

/**
 * Clear all auth state from localStorage.
 */
export function logout() {
  localStorage.removeItem('supplychainiq_jwt');
  localStorage.removeItem('supplychainiq_user_id');
  localStorage.removeItem('supplychainiq_email');
  localStorage.removeItem('supplychainiq_company_name');
  localStorage.removeItem('supplychainiq_company_type');
}

/**
 * Switch into one-click guest mode (no registration). Used by the
 * "Continue as guest" button on the login screen so judges can demo
 * without signing up.
 */
export function continueAsGuest() {
  logout();
  const guestId = 'guest_' + Date.now();
  localStorage.setItem('supplychainiq_user_id', guestId);
}

function _persistAuth(authResponse) {
  if (!authResponse) return;
  if (authResponse.access_token) {
    localStorage.setItem('supplychainiq_jwt', authResponse.access_token);
  }
  if (authResponse.user_id) {
    localStorage.setItem('supplychainiq_user_id', authResponse.user_id);
  }
  if (authResponse.email) {
    localStorage.setItem('supplychainiq_email', authResponse.email);
  }
  if (authResponse.company_name) {
    localStorage.setItem('supplychainiq_company_name', authResponse.company_name);
  }
  if (authResponse.company_type) {
    localStorage.setItem('supplychainiq_company_type', authResponse.company_type);
  }
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

  const jwt = localStorage.getItem('supplychainiq_jwt');
  const userId = localStorage.getItem('supplychainiq_user_id') || 'guest';
  const preferred = localStorage.getItem('supplychainiq_preferred_provider') || '';
  const headers = {};
  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  } else {
    headers['X-User-ID'] = userId;
  }
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
