import React from "react";
import { useCart } from "../context/CartContext";

export default function Navbar() {
  const { totalItemCount, currentView, setCurrentView, toggleCart } = useCart();

  return (
    <header className="navbar">
      <div className="nav-container">
        <button
          type="button"
          className="brand"
          onClick={() => setCurrentView("catalog")}
          aria-label="Novastore Home"
        >
          <div className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <path d="M16 10a4 4 0 0 1-8 0"></path>
            </svg>
          </div>
          <span className="brand-title">
            Nova<span>store</span>
          </span>
        </button>

        <nav className="nav-links">
          <button
            type="button"
            className={`nav-link-btn ${currentView === "catalog" ? "active" : ""}`}
            onClick={() => setCurrentView("catalog")}
          >
            Catalogue
          </button>
          <button
            type="button"
            className={`nav-link-btn ${currentView === "admin" ? "active" : ""}`}
            onClick={() => setCurrentView("admin")}
            title="Administrator Portal"
          >
            Admin
          </button>
        </nav>

        <div className="nav-actions">
          <button
            type="button"
            className={`cart-button-active ${currentView === "cart" ? "in-cart" : ""}`}
            onClick={toggleCart}
            aria-label={`Shopping Cart with ${totalItemCount} items`}
            title="View Shopping Cart"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
            <span className="cart-label">Cart</span>
            <span className="cart-badge">{totalItemCount}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
