/**
 * API Service for communicating with the Python Flask Backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * Fetch products with optional filters, search, and sorting.
 * @param {Object} params
 * @returns {Promise<{products: Array, count: number, filters: Object}>}
 */
export async function fetchProducts({
  search = "",
  category = "",
  minPrice = "",
  maxPrice = "",
  sort = "",
} = {}) {
  const query = new URLSearchParams();

  if (search && search.trim()) query.set("search", search.trim());
  if (category && category.trim() && category !== "All") query.set("category", category.trim());
  if (minPrice !== "" && minPrice !== null && minPrice !== undefined) query.set("min_price", minPrice);
  if (maxPrice !== "" && maxPrice !== null && maxPrice !== undefined) query.set("max_price", maxPrice);
  if (sort && sort.trim()) query.set("sort", sort.trim());

  const url = `${API_BASE}/products${query.toString() ? `?${query.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Failed to fetch products (${response.status})`);
  }

  return response.json();
}

/**
 * Fetch a single product's complete details by ID.
 * @param {number|string} id
 * @returns {Promise<Object>}
 */
export async function fetchProductById(id) {
  const response = await fetch(`${API_BASE}/products/${id}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Failed to fetch product #${id} (${response.status})`);
  }

  return response.json();
}

/**
 * Fetch distinct product categories with item counts.
 * @returns {Promise<Array<{name: string, count: number}>>}
 */
export async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || "Failed to fetch categories");
  }

  const data = await response.json();
  return data.categories || [];
}

/**
 * Create a new order with simulated checkout.
 * @param {Object} orderData
 * @returns {Promise<{message: string, order: Object}>}
 */
export async function createOrder(orderData) {
  const response = await fetch(`${API_BASE}/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(orderData),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Failed to place order (${response.status})`);
  }

  return data;
}

/**
 * Retrieve order confirmation details by reference code.
 * @param {string} reference
 * @returns {Promise<{order: Object}>}
 */
export async function fetchOrderByReference(reference) {
  const cleanRef = encodeURIComponent(reference.trim().toUpperCase());
  const response = await fetch(`${API_BASE}/orders/${cleanRef}`);

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Order '${reference}' not found`);
  }

  return data;
}
