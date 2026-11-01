import React, { useState, useEffect, useCallback } from "react";
import {
  fetchAdminOrders,
  fetchAdminOrderById,
  updateAdminOrderStatus,
} from "../../services/adminApi";

const STATUS_OPTIONS = ["ALL", "PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED"];

const ALLOWED_STATUS_TRANSITIONS = {
  PENDING: ["PENDING", "CONFIRMED", "CANCELLED"],
  CONFIRMED: ["CONFIRMED", "SHIPPED", "CANCELLED"],
  SHIPPED: ["SHIPPED", "DELIVERED", "CANCELLED"],
  DELIVERED: ["DELIVERED"],
  CANCELLED: ["CANCELLED"],
};


export default function AdminOrdersPage({ initialOrderRef = null }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  // Order Details Modal
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const notify = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAdminOrders({
        status: statusFilter,
        search,
      });
      setOrders(data.orders || []);
    } catch (err) {
      setError(err.message || "Failed to load orders.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // If initialOrderRef was passed from Dashboard
  useEffect(() => {
    if (initialOrderRef) {
      openOrderDetails(initialOrderRef);
    }
  }, [initialOrderRef]);

  const openOrderDetails = async (idOrRef) => {
    try {
      setModalLoading(true);
      const data = await fetchAdminOrderById(idOrRef);
      setSelectedOrder(data.order);
      setSelectedStatus(data.order.status);
    } catch (err) {
      notify(err.message || "Failed to fetch order details.", "error");
    } finally {
      setModalLoading(false);
    }
  };

  const handleStatusUpdate = async () => {
    if (!selectedOrder || !selectedStatus) return;
    if (selectedStatus === selectedOrder.status) return;

    try {
      setUpdatingStatus(true);
      const res = await updateAdminOrderStatus(selectedOrder.order_reference, selectedStatus);
      notify(`Order ${selectedOrder.order_reference} status updated to ${selectedStatus}.`);
      setSelectedOrder(res.order);

      // Update in local list
      setOrders((prev) =>
        prev.map((o) => (o.id === res.order.id ? { ...o, status: res.order.status } : o))
      );
    } catch (err) {
      notify(err.message || "Failed to update order status.", "error");
    } finally {
      setUpdatingStatus(false);
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case "CONFIRMED":
        return "status-badge-confirmed";
      case "SHIPPED":
        return "status-badge-shipped";
      case "DELIVERED":
        return "status-badge-delivered";
      case "CANCELLED":
        return "status-badge-cancelled";
      case "PENDING":
      default:
        return "status-badge-pending";
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
          <h1 className="admin-page-title">Customer Order Fulfillment</h1>
          <p className="admin-page-subtitle">Track customer orders, review itemized purchase snapshots, and manage delivery status.</p>
        </div>
        <button
          type="button"
          className="admin-btn admin-btn-secondary"
          onClick={loadOrders}
          title="Refresh orders list"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          Refresh Orders
        </button>
      </div>

      {/* Filters */}
      <div className="admin-toolbar-card">
        <div className="admin-search-group">
          <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            className="admin-search-input"
            placeholder="Search by customer name, email, phone, or reference..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="admin-filter-group">
          <label htmlFor="order-status-filter" className="admin-filter-label">Filter Status:</label>
          <select
            id="order-status-filter"
            className="admin-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {STATUS_OPTIONS.map((st) => (
              <option key={st} value={st}>
                {st === "ALL" ? "All Statuses" : st}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="admin-alert admin-alert-danger" role="alert">
          <span>{error}</span>
        </div>
      )}

      {/* Orders Table */}
      <div className="admin-card">
        <div className="admin-card-header-flex">
          <span className="admin-table-summary">
            Showing <strong>{orders.length}</strong> recorded orders
          </span>
        </div>

        {loading ? (
          <div className="admin-loading-card">
            <div className="button-spinner"></div>
            <span>Loading orders...</span>
          </div>
        ) : orders.length === 0 ? (
          <p className="empty-notice">No orders found matching your search criteria.</p>
        ) : (
          <div className="admin-table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Order Reference</th>
                  <th>Customer Information</th>
                  <th>Order Date</th>
                  <th>Items</th>
                  <th>Total Amount</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((ord) => (
                  <tr key={ord.id}>
                    <td>
                      <span className="order-ref-code">{ord.order_reference}</span>
                      <div className="subtext">ID #{ord.id}</div>
                    </td>
                    <td>
                      <strong>{ord.customer_name}</strong>
                      <div className="subtext">{ord.customer_email}</div>
                      <div className="subtext">{ord.customer_phone}</div>
                    </td>
                    <td>
                      {new Date(ord.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                      <div className="subtext">
                        {new Date(ord.created_at).toLocaleTimeString(undefined, {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </td>
                    <td>
                      <span className="order-items-badge">
                        {ord.items ? ord.items.length : 1} item(s)
                      </span>
                    </td>
                    <td>
                      <strong className="order-total-price">${ord.total_amount.toFixed(2)}</strong>
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusBadgeClass(ord.status)}`}>
                        {ord.status}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        type="button"
                        className="admin-btn admin-btn-xs admin-btn-primary"
                        onClick={() => openOrderDetails(ord.order_reference)}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Order Details Modal */}
      {selectedOrder && (
        <div className="modal-backdrop" onClick={() => setSelectedOrder(null)}>
          <div className="modal-dialog admin-modal-order" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Order #{selectedOrder.id} — <span className="order-ref-code">{selectedOrder.order_reference}</span></h3>
                <span className="subtext">
                  Placed on {new Date(selectedOrder.created_at).toLocaleString()}
                </span>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedOrder(null)}
              >
                ✕
              </button>
            </div>

            <div className="modal-body admin-order-modal-body">
              {/* Customer & Delivery Information */}
              <div className="admin-order-info-grid">
                <div className="order-info-card">
                  <h4>Customer Contact</h4>
                  <p><strong>Name:</strong> {selectedOrder.customer_name}</p>
                  <p><strong>Email:</strong> {selectedOrder.customer_email}</p>
                  <p><strong>Phone:</strong> {selectedOrder.customer_phone}</p>
                </div>

                <div className="order-info-card">
                  <h4>Shipping Address</h4>
                  <p><strong>Street:</strong> {selectedOrder.delivery_address}</p>
                  <p><strong>City:</strong> {selectedOrder.city}</p>
                  <p><strong>Postal Code:</strong> {selectedOrder.postal_code}</p>
                </div>
              </div>

              {/* Status Update Control */}
              <div className="admin-order-status-banner">
                <div className="status-banner-left">
                  <span className="status-label-heading">Current Status:</span>
                  <span className={`status-badge ${getStatusBadgeClass(selectedOrder.status)}`}>
                    {selectedOrder.status}
                  </span>
                </div>
                <div className="status-banner-right">
                  <label htmlFor="modal-status-select" className="subtext">Update Status:</label>
                  <select
                    id="modal-status-select"
                    className="admin-select"
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    disabled={updatingStatus || (ALLOWED_STATUS_TRANSITIONS[selectedOrder.status]?.length <= 1)}
                  >
                    {STATUS_OPTIONS.filter((s) => s !== "ALL").map((st) => {
                      const allowed = ALLOWED_STATUS_TRANSITIONS[selectedOrder.status] || [];
                      const isAllowed = allowed.includes(st);
                      return (
                        <option key={st} value={st} disabled={!isAllowed}>
                          {st}{!isAllowed ? " (Not allowed)" : ""}
                        </option>
                      );
                    })}
                  </select>
                  <button
                    type="button"
                    className="admin-btn admin-btn-sm admin-btn-primary"
                    onClick={handleStatusUpdate}
                    disabled={
                      updatingStatus ||
                      selectedStatus === selectedOrder.status ||
                      !(ALLOWED_STATUS_TRANSITIONS[selectedOrder.status] || []).includes(selectedStatus)
                    }
                  >
                    {updatingStatus ? "Updating..." : "Save Status"}
                  </button>
                </div>
              </div>

              {/* Purchased Items Snapshot */}
              <div className="admin-order-items-section">
                <h4>Purchased Items (Purchase-Time Snapshot)</h4>
                <div className="admin-table-responsive">
                  <table className="admin-table admin-order-items-table">
                    <thead>
                      <tr>
                        <th>Product Name</th>
                        <th style={{ textAlign: "right" }}>Unit Price</th>
                        <th style={{ textAlign: "center" }}>Qty</th>
                        <th style={{ textAlign: "right" }}>Line Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedOrder.items && selectedOrder.items.map((item) => (
                        <tr key={item.id}>
                          <td>
                            <strong>{item.product_name}</strong>
                            <div className="subtext">Product ID #{item.product_id}</div>
                          </td>
                          <td style={{ textAlign: "right" }}>${item.unit_price.toFixed(2)}</td>
                          <td style={{ textAlign: "center" }}>{item.quantity}</td>
                          <td style={{ textAlign: "right" }}>
                            <strong>${item.line_total.toFixed(2)}</strong>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Financial Summary */}
                <div className="admin-order-totals-box">
                  <div className="order-total-row">
                    <span>Subtotal:</span>
                    <span>${selectedOrder.subtotal.toFixed(2)}</span>
                  </div>
                  <div className="order-total-row">
                    <span>Delivery Fee:</span>
                    <span>
                      {selectedOrder.delivery_fee === 0 ? "FREE" : `$${selectedOrder.delivery_fee.toFixed(2)}`}
                    </span>
                  </div>
                  <div className="order-total-row total-highlight">
                    <span>Grand Total:</span>
                    <span>${selectedOrder.total_amount.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="admin-btn admin-btn-secondary"
                onClick={() => setSelectedOrder(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
