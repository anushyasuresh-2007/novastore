/**
 * API Service for Novastore Administrator Dashboard.
 * Uses secure HttpOnly cookie authentication ('admin_session') and synchronizer CSRF tokens.
 * Tokens are never stored in localStorage to protect against XSS token exfiltration.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

// In-memory synchronizer CSRF token
let currentCsrfToken = null;

/**
 * Retrieve CSRF token from memory or non-HttpOnly readable cookie.
 */
export function getCsrfToken() {
  if (currentCsrfToken) return currentCsrfToken;
  if (typeof document !== "undefined") {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (match) {
      currentCsrfToken = decodeURIComponent(match[1]);
      return currentCsrfToken;
    }
  }
  return null;
}

/**
 * Set in-memory CSRF token.
 */
export function setCsrfToken(token) {
  currentCsrfToken = token || null;
}

/**
 * Helper to make authorized requests with HttpOnly cookies and CSRF protection.
 */
async function authorizedFetch(endpoint, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  // State-changing requests (POST, PUT, PATCH, DELETE) require a synchronizer CSRF token
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers["X-CSRF-Token"] = csrf;
    }
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: "include", // Ensure browser sends HttpOnly admin_session cookie
  });

  const data = await response.json().catch(() => ({}));

  // Automatically refresh in-memory CSRF token if returned in response
  if (data.csrf_token) {
    setCsrfToken(data.csrf_token);
  }

  if (!response.ok) {
    if (response.status === 401) {
      setCsrfToken(null);
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
 * Session token is stored directly in an HttpOnly cookie by the server.
 */
export async function adminLogin(identifier, password) {
  const response = await fetch(`${API_BASE}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username: identifier, password }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Login failed. Please verify credentials.");
  }

  if (data.csrf_token) {
    setCsrfToken(data.csrf_token);
  }

  // Purge any legacy localStorage token from earlier versions
  try {
    localStorage.removeItem("novastore_admin_token");
  } catch {}

  return data;
}

/**
 * Log out administrator session, invalidating session on the server and clearing cookies.
 */
export async function adminLogout() {
  try {
    await authorizedFetch("/admin/logout", { method: "POST" });
  } finally {
    setCsrfToken(null);
    try {
      localStorage.removeItem("novastore_admin_token");
    } catch {}
  }
}

/**
 * Verify current administrator session and fetch profile with fresh CSRF token.
 */
export async function fetchAdminMe() {
  const data = await authorizedFetch("/admin/me");
  if (data.csrf_token) {
    setCsrfToken(data.csrf_token);
  }
  return data;
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
