/**
 * API Service for Novastore Administrator Dashboard.
 * Handles authentication headers, token persistence, and administrative CRUD endpoints.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const ADMIN_TOKEN_KEY = "novastore_admin_token";

/**
 * Get stored administrator token from localStorage.
 */
export function getAdminToken() {
  try {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
  } catch (err) {
    console.error("Error reading admin token from localStorage:", err);
    return null;
  }
}

/**
 * Save administrator token to localStorage.
 */
export function setAdminToken(token) {
  try {
    if (token) {
      localStorage.setItem(ADMIN_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    }
  } catch (err) {
    console.error("Error storing admin token:", err);
  }
}

/**
 * Remove administrator token from localStorage.
 */
export function clearAdminToken() {
  try {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  } catch (err) {
    console.error("Error clearing admin token:", err);
  }
}

/**
 * Helper to make authorized requests with bearer token.
 */
async function authorizedFetch(endpoint, options = {}) {
  const token = getAdminToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401) {
      // Clear expired or invalid token
      clearAdminToken();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("admin:unauthorized"));
      }
    }
    throw new Error(data.error || `Admin request failed (${response.status})`);
  }

  return data;
}

/**
 * Log in administrator with username/email and password.
 */
export async function adminLogin(identifier, password) {
  const response = await fetch(`${API_BASE}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: identifier, password }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Login failed. Please verify credentials.");
  }

  if (data.token) {
    setAdminToken(data.token);
  }

  return data;
}

/**
 * Log out administrator session.
 */
export async function adminLogout() {
  try {
    await authorizedFetch("/admin/logout", { method: "POST" });
  } finally {
    clearAdminToken();
  }
}

/**
 * Verify current administrator session and fetch profile.
 */
export async function fetchAdminMe() {
  return authorizedFetch("/admin/me");
}

/**
 * Fetch dashboard statistics.
 */
export async function fetchAdminStats() {
  return authorizedFetch("/admin/stats");
}

/**
 * Fetch all products for administrative view.
 */
export async function fetchAdminProducts({ search = "", category = "", status = "" } = {}) {
  const query = new URLSearchParams();
  if (search && search.trim()) query.set("search", search.trim());
  if (category && category.trim() && category !== "All") query.set("category", category.trim());
  if (status && status.trim() && status !== "all") query.set("status", status.trim());

  return authorizedFetch(`/admin/products${query.toString() ? `?${query.toString()}` : ""}`);
}

/**
 * Create a new product.
 */
export async function createAdminProduct(productData) {
  return authorizedFetch("/admin/products", {
    method: "POST",
    body: JSON.stringify(productData),
  });
}

/**
 * Update an existing product.
 */
export async function updateAdminProduct(productId, productData) {
  return authorizedFetch(`/admin/products/${productId}`, {
    method: "PUT",
    body: JSON.stringify(productData),
  });
}

/**
 * Safely delete or archive a product.
 */
export async function deleteAdminProduct(productId) {
  return authorizedFetch(`/admin/products/${productId}`, {
    method: "DELETE",
  });
}

/**
 * Fetch orders for administration with optional filtering.
 */
export async function fetchAdminOrders({ status = "", search = "" } = {}) {
  const query = new URLSearchParams();
  if (status && status.trim() && status !== "ALL") query.set("status", status.trim());
  if (search && search.trim()) query.set("search", search.trim());

  return authorizedFetch(`/admin/orders${query.toString() ? `?${query.toString()}` : ""}`);
}

/**
 * Fetch a single order's full details.
 */
export async function fetchAdminOrderById(idOrRef) {
  return authorizedFetch(`/admin/orders/${encodeURIComponent(idOrRef)}`);
}

/**
 * Update an order's status.
 */
export async function updateAdminOrderStatus(idOrRef, newStatus) {
  return authorizedFetch(`/admin/orders/${encodeURIComponent(idOrRef)}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: newStatus }),
  });
}
