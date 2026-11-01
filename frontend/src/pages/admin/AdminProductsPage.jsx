import React, { useState, useEffect, useCallback } from "react";
import {
  fetchAdminProducts,
  createAdminProduct,
  updateAdminProduct,
  deleteAdminProduct,
} from "../../services/adminApi";
import { fetchCategories } from "../../services/api";

const EMPTY_FORM = {
  name: "",
  description: "",
  category: "Electronics",
  price: "",
  stock_quantity: "",
  image_path: "",
  is_active: true,
};

export default function AdminProductsPage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  // Delete confirmation state
  const [productToDelete, setProductToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const notify = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadCategories = async () => {
    try {
      const cats = await fetchCategories();
      setCategories(cats);
    } catch (err) {
      console.warn("Could not fetch categories:", err);
    }
  };

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAdminProducts({
        search,
        category: categoryFilter,
        status: statusFilter,
      });
      setProducts(data.products || []);
    } catch (err) {
      setError(err.message || "Failed to load products.");
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, statusFilter]);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const handleOpenAddModal = () => {
    setEditingProduct(null);
    setFormData(EMPTY_FORM);
    setFormErrors({});
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      description: product.description,
      category: product.category,
      price: product.price,
      stock_quantity: product.stock_quantity,
      image_path: product.image_path || "",
      is_active: product.is_active,
    });
    setFormErrors({});
    setIsModalOpen(true);
  };

  const validateForm = () => {
    const errors = {};
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      errors.name = "Product name must be at least 2 characters long.";
    }
    if (!formData.description.trim() || formData.description.trim().length < 5) {
      errors.description = "Product description must be at least 5 characters long.";
    }
    if (!formData.category.trim()) {
      errors.category = "Please select or enter a category.";
    }
    const priceNum = parseFloat(formData.price);
    if (isNaN(priceNum) || priceNum < 0) {
      errors.price = "Price must be a valid non-negative number.";
    }
    const stockNum = parseInt(formData.stock_quantity, 10);
    if (isNaN(stockNum) || stockNum < 0) {
      errors.stock_quantity = "Stock quantity must be a non-negative integer.";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      setSubmitting(true);
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        category: formData.category.trim(),
        price: parseFloat(formData.price),
        stock_quantity: parseInt(formData.stock_quantity, 10),
        image_path: formData.image_path.trim() || "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
        is_active: Boolean(formData.is_active),
      };

      if (editingProduct) {
        await updateAdminProduct(editingProduct.id, payload);
        notify(`Product #${editingProduct.id} ('${payload.name}') updated successfully.`);
      } else {
        const res = await createAdminProduct(payload);
        notify(`New product #${res.product.id} created successfully.`);
      }

      setIsModalOpen(false);
      loadProducts();
      loadCategories();
    } catch (err) {
      notify(err.message || "Failed to save product.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickStock = async (product, delta) => {
    const newStock = Math.max(0, product.stock_quantity + delta);
    try {
      await updateAdminProduct(product.id, { stock_quantity: newStock });
      notify(`Updated stock for "${product.name}" to ${newStock}.`);
      setProducts((prev) =>
        prev.map((p) => (p.id === product.id ? { ...p, stock_quantity: newStock } : p))
      );
    } catch (err) {
      notify(err.message || "Failed to update stock.", "error");
    }
  };

  const handleDeleteConfirm = async () => {
    if (!productToDelete) return;
    try {
      setDeleting(true);
      const res = await deleteAdminProduct(productToDelete.id);
      notify(res.message || "Product processed successfully.");
      setProductToDelete(null);
      loadProducts();
      loadCategories();
    } catch (err) {
      notify(err.message || "Failed to delete product.", "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="admin-page-container">
      {/* Toast Notification */}
      {notification && (
        <div className={`admin-toast admin-toast-${notification.type}`} role="alert">
          {notification.msg}
        </div>
      )}

      {/* Page Header */}
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Product Inventory Management</h1>
          <p className="admin-page-subtitle">Add new items, update prices, manage stock quantities, and archive products safely.</p>
        </div>
        <button
          type="button"
          className="admin-btn admin-btn-primary"
          onClick={handleOpenAddModal}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          Add New Product
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="admin-toolbar-card">
        <div className="admin-search-group">
          <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            className="admin-search-input"
            placeholder="Search by title or SKU..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="admin-filter-group">
          <label htmlFor="cat-filter" className="admin-filter-label">Category:</label>
          <select
            id="cat-filter"
            className="admin-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="All">All Categories</option>
            {categories.map((c) => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>

          <label htmlFor="status-filter" className="admin-filter-label">Status:</label>
          <select
            id="status-filter"
            className="admin-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive / Archived</option>
            <option value="out_of_stock">Out of Stock (0)</option>
            <option value="low_stock">Low Stock (≤5)</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="admin-alert admin-alert-danger" role="alert">
          <span>{error}</span>
        </div>
      )}

      {/* Products Table */}
      <div className="admin-card">
        <div className="admin-card-header-flex">
          <span className="admin-table-summary">
            Showing <strong>{products.length}</strong> products
          </span>
        </div>

        {loading ? (
          <div className="admin-loading-card">
            <div className="button-spinner"></div>
            <span>Loading product inventory...</span>
          </div>
        ) : products.length === 0 ? (
          <p className="empty-notice">No products found matching your filter criteria.</p>
        ) : (
          <div className="admin-table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th style={{ width: "60px" }}>ID</th>
                  <th style={{ width: "64px" }}>Image</th>
                  <th>Product Details</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Stock Quantity</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className={!p.is_active ? "row-inactive" : ""}>
                    <td>
                      <span className="product-id-tag">#{p.id}</span>
                    </td>
                    <td>
                      <img
                        src={p.image_path}
                        alt={p.name}
                        className="admin-prod-thumb"
                        onError={(e) => {
                          e.target.src = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=120&q=80";
                        }}
                      />
                    </td>
                    <td>
                      <strong className="product-name-title">{p.name}</strong>
                      <p className="product-desc-snippet">{p.description}</p>
                    </td>
                    <td>
                      <span className="category-tag">{p.category}</span>
                    </td>
                    <td>
                      <strong className="product-price-val">${p.price.toFixed(2)}</strong>
                    </td>
                    <td>
                      <div className="admin-stock-control">
                        <button
                          type="button"
                          className="stock-btn"
                          onClick={() => handleQuickStock(p, -1)}
                          disabled={p.stock_quantity <= 0}
                          title="Decrease stock by 1"
                        >
                          –
                        </button>
                        <span className={`stock-count ${p.stock_quantity === 0 ? "stock-zero" : p.stock_quantity <= 5 ? "stock-low" : ""}`}>
                          {p.stock_quantity}
                        </span>
                        <button
                          type="button"
                          className="stock-btn"
                          onClick={() => handleQuickStock(p, 1)}
                          title="Increase stock by 1"
                        >
                          +
                        </button>
                      </div>
                    </td>
                    <td>
                      {p.is_active ? (
                        <span className="status-badge status-badge-confirmed">Active</span>
                      ) : (
                        <span className="status-badge status-badge-cancelled">Inactive</span>
                      )}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div className="table-actions-inline">
                        <button
                          type="button"
                          className="admin-btn admin-btn-xs admin-btn-secondary"
                          onClick={() => handleOpenEditModal(p)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="admin-btn admin-btn-xs admin-btn-danger"
                          onClick={() => setProductToDelete(p)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add / Edit Product Modal */}
      {isModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <div className="modal-dialog admin-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingProduct ? `Edit Product #${editingProduct.id}` : "Add New Catalogue Product"}</h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div className="modal-body admin-form-grid">
                <div className="form-group full-width">
                  <label htmlFor="prod-name">Product Name *</label>
                  <input
                    id="prod-name"
                    type="text"
                    className="admin-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Studio Reference Headphones"
                    required
                  />
                  {formErrors.name && <span className="field-error">{formErrors.name}</span>}
                </div>

                <div className="form-group">
                  <label htmlFor="prod-cat">Category *</label>
                  <input
                    id="prod-cat"
                    type="text"
                    list="cat-suggestions"
                    className="admin-input"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    placeholder="e.g. Audio, Electronics"
                    required
                  />
                  <datalist id="cat-suggestions">
                    <option value="Electronics" />
                    <option value="Audio" />
                    <option value="Accessories" />
                    <option value="Home & Office" />
                    <option value="Wearables" />
                    <option value="Photography" />
                  </datalist>
                  {formErrors.category && <span className="field-error">{formErrors.category}</span>}
                </div>

                <div className="form-group">
                  <label htmlFor="prod-price">Price ($ USD) *</label>
                  <input
                    id="prod-price"
                    type="number"
                    step="0.01"
                    min="0"
                    className="admin-input"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    placeholder="e.g. 49.99"
                    required
                  />
                  {formErrors.price && <span className="field-error">{formErrors.price}</span>}
                </div>

                <div className="form-group">
                  <label htmlFor="prod-stock">Stock Quantity *</label>
                  <input
                    id="prod-stock"
                    type="number"
                    min="0"
                    step="1"
                    className="admin-input"
                    value={formData.stock_quantity}
                    onChange={(e) => setFormData({ ...formData, stock_quantity: e.target.value })}
                    placeholder="e.g. 25"
                    required
                  />
                  {formErrors.stock_quantity && <span className="field-error">{formErrors.stock_quantity}</span>}
                </div>

                <div className="form-group">
                  <label htmlFor="prod-active">Catalogue Visibility</label>
                  <div className="checkbox-wrapper" style={{ marginTop: "10px" }}>
                    <label>
                      <input
                        id="prod-active"
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      />
                      {" "}Active in Storefront Catalogue
                    </label>
                  </div>
                </div>

                <div className="form-group full-width">
                  <label htmlFor="prod-img">Image URL</label>
                  <input
                    id="prod-img"
                    type="url"
                    className="admin-input"
                    value={formData.image_path}
                    onChange={(e) => setFormData({ ...formData, image_path: e.target.value })}
                    placeholder="https://images.unsplash.com/..."
                  />
                </div>

                <div className="form-group full-width">
                  <label htmlFor="prod-desc">Description *</label>
                  <textarea
                    id="prod-desc"
                    rows="3"
                    className="admin-textarea"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Detailed specifications, features, and dimensions..."
                    required
                  />
                  {formErrors.description && <span className="field-error">{formErrors.description}</span>}
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="admin-btn admin-btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="admin-btn admin-btn-primary"
                  disabled={submitting}
                >
                  {submitting ? "Saving Product..." : editingProduct ? "Save Changes" : "Create Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {productToDelete && (
        <div className="modal-backdrop" onClick={() => setProductToDelete(null)}>
          <div className="modal-dialog admin-modal-sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Delete Product Confirmation</h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setProductToDelete(null)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p>
                Are you sure you want to remove <strong>"{productToDelete.name}"</strong> (ID #{productToDelete.id})?
              </p>
              <div className="admin-delete-notice">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span>
                  <strong>Safety Guarantee:</strong> If this product has existing historical orders, it will be <em>safely deactivated</em> from the customer catalogue to protect order item records. It will never delete customer invoices.
                </span>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="admin-btn admin-btn-secondary"
                onClick={() => setProductToDelete(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="admin-btn admin-btn-danger"
                onClick={handleDeleteConfirm}
                disabled={deleting}
              >
                {deleting ? "Processing..." : "Confirm Deletion"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
