const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export async function listSessions() {
  const res = await fetch(`${API_BASE}/api/v1/sessions`);
  if (!res.ok) throw new Error('Failed to list sessions');
  return await res.json();
}

export async function getSession(id) {
  const res = await fetch(`${API_BASE}/api/v1/sessions/${id}`);
  if (!res.ok) throw new Error('Session not found');
  return await res.json();
}

export async function createSession(data) {
  const res = await fetch(`${API_BASE}/api/v1/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error('Failed to create');
  return await res.json();
}

export async function deleteSession(id) {
  const res = await fetch(`${API_BASE}/api/v1/sessions/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete');
}