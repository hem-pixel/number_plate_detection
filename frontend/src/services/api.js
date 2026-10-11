/**
 * API Service for Indian Vehicle Number Plate Recognition & College Fleet System
 * Includes Secure JWT Authentication and Role-Based User Management
 */

export const API_BASE_URL = 'http://localhost:8000/api/v1';
export const SERVER_ROOT = 'http://localhost:8000';
export const WS_URL = 'ws://localhost:8000/ws';

// ---------------- Token Storage & Helper ----------------

const TOKEN_KEY = 'anpr_auth_token';
const REFRESH_TOKEN_KEY = 'anpr_refresh_token';

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setAuthTokens(accessToken, refreshToken = null) {
  if (accessToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
  }
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearAuthTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getWsUrl() {
  const token = getAuthToken();
  if (token) {
    return `${WS_URL}?token=${encodeURIComponent(token)}`;
  }
  return WS_URL;
}

// Format image URL (handles relative static paths vs full URLs)
export function getImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (path.startsWith('/')) return `${SERVER_ROOT}${path}`;
  return `${SERVER_ROOT}/${path}`;
}

/**
 * Custom fetch wrapper that injects Authorization Bearer header
 */
async function secureFetch(url, options = {}) {
  const headers = { ...options.headers };
  const token = getAuthToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    // Notify application about session expiry if appropriate
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  }
  return res;
}

// ---------------- Authentication APIs ----------------

export async function login(email, password) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Invalid email or password');
  }
  const data = await res.json();
  setAuthTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout() {
  try {
    const refreshToken = getRefreshToken();
    await secureFetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (err) {
    console.error('Logout error:', err);
  } finally {
    clearAuthTokens();
  }
}

export async function fetchCurrentUser() {
  const res = await secureFetch(`${API_BASE_URL}/auth/me`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch current user profile');
  }
  return await res.json();
}

export async function refreshToken() {
  const refToken = getRefreshToken();
  if (!refToken) throw new Error('No refresh token available');

  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refToken }),
  });
  if (!res.ok) {
    clearAuthTokens();
    throw new Error('Refresh token expired or invalid');
  }
  const data = await res.json();
  setAuthTokens(data.access_token, data.refresh_token);
  return data;
}

// ---------------- User Management (ADMIN Only) ----------------

export async function fetchUsers(options = {}) {
  const params = new URLSearchParams();
  if (options.role) params.append('role', options.role);
  if (options.is_active !== undefined) params.append('is_active', options.is_active);
  if (options.search) params.append('search', options.search);
  if (options.skip !== undefined) params.append('skip', options.skip);
  if (options.limit !== undefined) params.append('limit', options.limit);

  const res = await secureFetch(`${API_BASE_URL}/users?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch users: ${res.statusText}`);
  }
  return await res.json();
}

export async function createUser(userData) {
  const res = await secureFetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create user: ${res.statusText}`);
  }
  return await res.json();
}

export async function updateUser(id, updateData) {
  const res = await secureFetch(`${API_BASE_URL}/users/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updateData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update user: ${res.statusText}`);
  }
  return await res.json();
}

export async function updateUserStatus(id, isActive) {
  const res = await secureFetch(`${API_BASE_URL}/users/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update user status: ${res.statusText}`);
  }
  return await res.json();
}

export async function resetUserPassword(id, newPassword) {
  const res = await secureFetch(`${API_BASE_URL}/users/${id}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_password: newPassword }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to reset password: ${res.statusText}`);
  }
  return await res.json();
}

export async function deleteUser(id) {
  const res = await secureFetch(`${API_BASE_URL}/users/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete user: ${res.statusText}`);
  }
  return await res.json();
}

// ---------------- College Vehicles CRUD ----------------

export async function fetchCollegeVehicles(options = {}) {
  const params = new URLSearchParams();
  if (typeof options === 'string') {
    if (options) params.append('status', options);
  } else if (typeof options === 'object' && options !== null) {
    if (options.status && options.status !== 'ALL') params.append('status', options.status);
    if (options.search) params.append('search', options.search);
    if (options.vehicle_type && options.vehicle_type !== 'ALL') params.append('vehicle_type', options.vehicle_type);
    if (options.current_status && options.current_status !== 'ALL') params.append('current_status', options.current_status);
    if (options.sort_by) params.append('sort_by', options.sort_by);
    if (options.sort_order) params.append('sort_order', options.sort_order);
    if (options.skip !== undefined) params.append('skip', options.skip);
    if (options.limit !== undefined) params.append('limit', options.limit);
  }

  const res = await secureFetch(`${API_BASE_URL}/college-vehicles?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch college vehicles: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchCollegeVehicleById(id) {
  const res = await secureFetch(`${API_BASE_URL}/college-vehicles/${id}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch vehicle details: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchCollegeVehicleHistory(id, limit = 50) {
  const res = await secureFetch(`${API_BASE_URL}/college-vehicles/${id}/history?limit=${limit}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch vehicle history: ${res.statusText}`);
  }
  return await res.json();
}

export async function createCollegeVehicle(data) {
  const res = await secureFetch(`${API_BASE_URL}/college-vehicles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create vehicle: ${res.statusText}`);
  }
  return await res.json();
}

export async function updateCollegeVehicle(id, data) {
  const res = await secureFetch(`${API_BASE_URL}/college-vehicles/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update vehicle: ${res.statusText}`);
  }
  return await res.json();
}

export async function deleteCollegeVehicle(id, hardDelete = false) {
  const query = hardDelete ? '?hard_delete=true' : '';
  const res = await secureFetch(`${API_BASE_URL}/college-vehicles/${id}${query}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete vehicle: ${res.statusText}`);
  }
  return await res.json();
}

// ---------------- Recognitions & Summary ----------------

export async function fetchDashboardSummary() {
  const res = await secureFetch(`${API_BASE_URL}/recognitions/summary`);
  if (!res.ok) {
    throw new Error(`Failed to fetch dashboard summary: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchRecognitions(options = {}) {
  const params = new URLSearchParams();
  if (options.limit) params.append('limit', options.limit);
  if (options.skip) params.append('skip', options.skip);
  if (options.category) params.append('vehicle_category', options.category);
  if (options.movement) params.append('movement_type', options.movement);
  if (options.search) params.append('search', options.search);

  const res = await secureFetch(`${API_BASE_URL}/recognitions?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch recognitions: ${res.statusText}`);
  }
  return await res.json();
}

export async function createManualRecognition(payload) {
  const res = await secureFetch(`${API_BASE_URL}/recognitions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to register recognition: ${res.statusText}`);
  }
  return await res.json();
}

// ---------------- Single Camera Configuration ----------------

export async function fetchCameraConfig() {
  const res = await secureFetch(`${API_BASE_URL}/camera/config`);
  if (!res.ok) {
    throw new Error(`Failed to fetch camera config: ${res.statusText}`);
  }
  return await res.json();
}

export async function updateCameraConfig(configData) {
  const res = await secureFetch(`${API_BASE_URL}/camera/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(configData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update camera config: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchLiveRecognitions(limit = 20) {
  const res = await secureFetch(`${API_BASE_URL}/recognitions/live?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch live recognitions: ${res.statusText}`);
  }
  return await res.json();
}
