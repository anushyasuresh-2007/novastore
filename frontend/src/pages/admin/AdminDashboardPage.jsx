import React, { useState, useEffect } from "react";
import { fetchAdminStats } from "../../services/adminApi";
import { useAdminAuth } from "../../context/AdminAuthContext";

export default function AdminDashboardPage({ onViewOrder }) {
  const { setActiveTab } = useAdminAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAdminStats();
      setStats(data);
    } catch (err) {
      setError(err.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

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
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Executive Overview</h1>
          <p className="admin-page-subtitle">Real-time inventory, sales analytics, and order fulfillment status.</p>
        </div>
        <div className="admin-header-actions">
          <button
            type="button"
            className="admin-btn admin-btn-secondary"
            onClick={loadStats}
            title="Refresh statistics"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh Data
          </button>
          <button
            type="button"
            className="admin-btn admin-btn-primary"
            onClick={() => setActiveTab("products")}
          >
            Manage Products →
          </button>
        </div>
      </div>

      {error && (
        <div className="admin-alert admin-alert-danger" role="alert">
          <span>{error}</span>
          <button type="button" onClick={loadStats}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className="admin-loading-card">
          <div className="button-spinner"></div>
          <span>Loading dashboard analytics...</span>
        </div>
      ) : stats ? (
        <>
          {/* Key Performance Indicators */}
          <div className="admin-metrics-grid">
            <div className="admin-metric-card">
              <div className="metric-icon metric-icon-blue">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                </svg>
              </div>
              <div className="metric-content">
                <span className="metric-label">Catalogue Products</span>
                <span className="metric-value">{stats.total_products}</span>
                <span className="metric-subtext">{stats.active_products} active in storefront</span>
              </div>
            </div>

            <div className="admin-metric-card">
              <div className="metric-icon metric-icon-green">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="1" x2="12" y2="23"></line>
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                </svg>
              </div>
              <div className="metric-content">
                <span className="metric-label">Total Sales (Recorded)</span>
                <span className="metric-value">${stats.total_sales.toFixed(2)}</span>
                <span className="metric-subtext">From {stats.total_orders} total customer orders</span>
              </div>
            </div>

            <div className="admin-metric-card">
              <div className="metric-icon metric-icon-purple">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="9" cy="21" r="1"></circle>
                  <circle cx="20" cy="21" r="1"></circle>
                  <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
              </div>
              <div className="metric-content">
                <span className="metric-label">Total Orders</span>
                <span className="metric-value">{stats.total_orders}</span>
                <span className="metric-subtext">Across all status levels</span>
              </div>
            </div>

            <div className="admin-metric-card">
              <div className="metric-icon metric-icon-amber">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 7h-7L10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"></path>
                </svg>
              </div>
              <div className="metric-content">
                <span className="metric-label">Total Inventory Units</span>
                <span className="metric-value">{stats.total_inventory}</span>
                <span className="metric-subtext">Warehouse units available</span>
              </div>
            </div>
          </div>

          {/* Status Breakdown Bar */}
          <div className="admin-card">
            <h3 className="admin-card-title">Order Fulfillment Status</h3>
            <div className="admin-status-pills">
              {Object.entries(stats.orders_by_status || {}).map(([st, count]) => (
                <div key={st} className="admin-status-pill-item">
                  <span className={`status-badge ${getStatusBadgeClass(st)}`}>{st}</span>
                  <span className="status-pill-count">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Orders Section */}
          <div className="admin-card">
            <div className="admin-card-header-flex">
              <div>
                <h3 className="admin-card-title">Recent Customer Orders</h3>
                <p className="admin-card-subtitle">Latest incoming orders requiring review or fulfillment.</p>
              </div>
              <button
                type="button"
                className="admin-btn admin-btn-sm admin-btn-secondary"
                onClick={() => setActiveTab("orders")}
              >
                View All Orders ({stats.total_orders}) →
              </button>
            </div>

            {stats.recent_orders && stats.recent_orders.length > 0 ? (
              <div className="admin-table-responsive">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Order Ref</th>
                      <th>Customer</th>
                      <th>Date</th>
                      <th>Delivery City</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_orders.map((ord) => (
                      <tr key={ord.id}>
                        <td>
                          <span className="order-ref-code">{ord.order_reference}</span>
                        </td>
                        <td>
                          <strong>{ord.customer_name}</strong>
                          <div className="subtext">{ord.customer_email}</div>
                        </td>
                        <td>
                          {new Date(ord.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </td>
                        <td>{ord.city}</td>
                        <td>
                          <strong>${ord.total_amount.toFixed(2)}</strong>
                        </td>
                        <td>
                          <span className={`status-badge ${getStatusBadgeClass(ord.status)}`}>
                            {ord.status}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="admin-table-action-btn"
                            onClick={() => {
                              if (onViewOrder) {
                                onViewOrder(ord.order_reference);
                              } else {
                                setActiveTab("orders");
                              }
                            }}
                          >
                            Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-notice">No orders recorded yet.</p>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
