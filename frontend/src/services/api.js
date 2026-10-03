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

export async function fetchCollegeVehicles(status = null, search = '') {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (search) params.append('search', search);

  const res = await fetch(`${API_BASE_URL}/college-vehicles?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch college vehicles: ${res.statusText}`);
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

export async function deleteCollegeVehicle(id) {
  const res = await fetch(`${API_BASE_URL}/college-vehicles/${id}`, {
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
