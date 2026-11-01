/**
 * API Service for communicating with the Python Flask Backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * Fetch products with optional filters, search, and sorting.
 * @param {Object} params
 * @param {string} [params.search]
 * @param {string} [params.category]
 * @param {number|string} [params.minPrice]
 * @param {number|string} [params.maxPrice]
 * @param {string} [params.sort]
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
