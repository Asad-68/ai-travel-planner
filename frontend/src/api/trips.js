const API_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

function authHeader() {
  const token = localStorage.getItem("wanderly_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function planTrip(formData) {
  const res = await fetch(`${API_URL}/api/trips/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(formData),
  });
  const data = await res.json();
  // Handle envelope if the node proxy hasn't restarted yet
  if (data.data && typeof data.data === "object") {
    return { ...data.data, _tripId: data._tripId };
  }
  return data;
}

export async function fetchCities() {
  const res = await fetch(`${API_URL}/api/trips/cities`);
  const data = await res.json();
  return Array.isArray(data) ? data : (data.data || []);
}

export async function saveItinerary(tripId, title) {
  const res = await fetch(`${API_URL}/api/trips/save/${tripId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function getSavedTrips() {
  const res = await fetch(`${API_URL}/api/trips/saved`, {
    headers: { ...authHeader() },
  });
  return res.json();
}

export async function deleteTrip(tripId) {
  const res = await fetch(`${API_URL}/api/trips/saved/${tripId}`, {
    method: "DELETE",
    headers: { ...authHeader() },
  });
  return res.json();
}
