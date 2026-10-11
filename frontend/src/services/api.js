/**
 * API Service for Indian Vehicle Number Plate Recognition & College Fleet System
 */

export const API_BASE_URL = 'http://localhost:8000/api/v1';
export const SERVER_ROOT = 'http://localhost:8000';
export const WS_URL = 'ws://localhost:8000/ws';

export function getWsUrl() {
  return WS_URL;
}

// Format image URL (handles relative static paths vs full URLs)
export function getImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (path.startsWith('/')) return `${SERVER_ROOT}${path}`;
  return `${SERVER_ROOT}/${path}`;
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

  const res = await fetch(`${API_BASE_URL}/college-vehicles?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch college vehicles: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchCollegeVehicleById(id) {
  const res = await fetch(`${API_BASE_URL}/college-vehicles/${id}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch vehicle details: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchCollegeVehicleHistory(id, limit = 50) {
  const res = await fetch(`${API_BASE_URL}/college-vehicles/${id}/history?limit=${limit}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch vehicle history: ${res.statusText}`);
  }
  return await res.json();
}

export async function createCollegeVehicle(data) {
  const res = await fetch(`${API_BASE_URL}/college-vehicles`, {
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
  const res = await fetch(`${API_BASE_URL}/college-vehicles/${id}`, {
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
  const res = await fetch(`${API_BASE_URL}/college-vehicles/${id}${query}`, {
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
  const res = await fetch(`${API_BASE_URL}/recognitions/summary`);
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

  const res = await fetch(`${API_BASE_URL}/recognitions?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch recognitions: ${res.statusText}`);
  }
  return await res.json();
}

export async function createManualRecognition(payload) {
  const res = await fetch(`${API_BASE_URL}/recognitions`, {
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
  const res = await fetch(`${API_BASE_URL}/camera/config`);
  if (!res.ok) {
    throw new Error(`Failed to fetch camera config: ${res.statusText}`);
  }
  return await res.json();
}

export async function updateCameraConfig(configData) {
  const res = await fetch(`${API_BASE_URL}/camera/config`, {
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
  const res = await fetch(`${API_BASE_URL}/recognitions/live?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch live recognitions: ${res.statusText}`);
  }
  return await res.json();
}

