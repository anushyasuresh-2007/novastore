import React from "react";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useCart } from "../../context/CartContext";

export default function AdminNavbar() {
  const { admin, activeTab, setActiveTab, logout } = useAdminAuth();
  const { setCurrentView } = useCart();

  return (
    <header className="admin-navbar">
      <div className="admin-nav-container">
        <div className="admin-brand-group">
          <button
            type="button"
            className="brand admin-brand"
            onClick={() => setActiveTab("dashboard")}
            aria-label="Novastore Admin"
          >
            <div className="brand-icon admin-brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </div>
            <span className="brand-title">
              Nova<span>store</span>
            </span>
          </button>
          <span className="admin-portal-badge">Admin Portal</span>
        </div>

        <nav className="admin-nav-links" aria-label="Admin Navigation">
          <button
            type="button"
            className={`admin-nav-link ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
            aria-label="View Dashboard"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <span>Dashboard</span>
          </button>
          <button
            type="button"
            className={`admin-nav-link ${activeTab === "products" ? "active" : ""}`}
            onClick={() => setActiveTab("products")}
            aria-label="Manage Products"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            </svg>
            <span>Products</span>
          </button>
          <button
            type="button"
            className={`admin-nav-link ${activeTab === "orders" ? "active" : ""}`}
            onClick={() => setActiveTab("orders")}
            aria-label="Manage Orders"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
            <span>Orders</span>
          </button>
        </nav>

        <div className="admin-nav-actions">
          {admin && (
            <div className="admin-user-pill" title={`Logged in as ${admin.email}`}>
              <div className="admin-avatar">
                {admin.username.charAt(0).toUpperCase()}
              </div>
              <span className="admin-username">{admin.username}</span>
            </div>
          )}

          <button
            type="button"
            className="admin-storefront-btn"
            onClick={() => setCurrentView("catalog")}
            aria-label="View public storefront"
            title="View public storefront"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
            <span className="admin-btn-text">Storefront</span>
          </button>

          <button
            type="button"
            className="admin-logout-btn"
            onClick={logout}
            aria-label="Sign out of admin dashboard"
            title="Sign out of admin dashboard"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            <span className="admin-btn-text">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
