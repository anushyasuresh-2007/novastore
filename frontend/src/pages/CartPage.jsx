import React from "react";
import { useCart } from "../context/CartContext";
import { formatCurrency } from "../utils/currency";

export default function CartPage() {
  const {
    cartItems,
    totalItemCount,
    subtotal,
    deliveryFee,
    totalAmount,
    updateQuantity,
    removeFromCart,
    clearCart,
    setCurrentView,
    goToCheckout,
  } = useCart();

  const fallbackImage = "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80";

  if (cartItems.length === 0) {
    return (
      <main className="cart-page-container">
        <div className="cart-empty-state">
          <div className="cart-empty-icon-wrap">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
          </div>
          <h2 className="cart-empty-title">Your Shopping Cart is Empty</h2>
          <p className="cart-empty-subtitle">
            Looks like you haven't added any products to your cart yet. Discover our top-tier catalog of tech and lifestyle essentials.
          </p>
          <button
            type="button"
            className="btn-continue-shopping"
            onClick={() => setCurrentView("catalog")}
          >
            ← Explore Catalog
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="cart-page-container">
      <div className="cart-header-row">
        <div>
          <h1 className="cart-title">Shopping Cart</h1>
          <p className="cart-subtitle">
            Review your selected items ({totalItemCount} {totalItemCount === 1 ? "item" : "items"})
          </p>
        </div>
        <div className="cart-header-actions">
          <button
            type="button"
            className="btn-text-secondary"
            onClick={() => setCurrentView("catalog")}
          >
            ← Continue Shopping
          </button>
          <button
            type="button"
            className="btn-clear-cart"
            onClick={clearCart}
            title="Remove all items from cart"
          >
            Clear Cart
          </button>
        </div>
      </div>

      <div className="cart-layout-grid">
        {/* Cart Items List */}
        <div className="cart-items-panel">
          <div className="cart-items-table-header">
            <span>Product</span>
            <span style={{ textAlign: "center" }}>Quantity</span>
            <span style={{ textAlign: "right" }}>Total</span>
          </div>

          <div className="cart-items-list">
            {cartItems.map((item) => {
              const lineTotal = (item.price * item.quantity).toFixed(2);
              const isAtMaxStock = item.quantity >= item.stock_quantity;

              return (
                <div key={item.id} className="cart-item-row" id={`cart-item-${item.id}`}>
                  {/* Thumbnail & Product Details */}
                  <div className="cart-item-product-info">
                    <img
                      src={item.image_path || fallbackImage}
                      alt={item.name}
                      className="cart-item-image"
                      onError={(e) => { e.target.src = fallbackImage; }}
                    />
                    <div className="cart-item-meta">
                      <span className="cart-item-category">{item.category}</span>
                      <h3 className="cart-item-name">{item.name}</h3>
                      <span className="cart-item-unit-price">{formatCurrency(item.price, item.currency)} each</span>
                      <span className="cart-item-stock-hint">
                        {item.stock_quantity} available in stock
                      </span>
                    </div>
                  </div>

                  {/* Quantity Stepper */}
                  <div className="cart-item-qty-container">
                    <div className="qty-stepper">
                      <button
                        type="button"
                        className="qty-btn"
                        onClick={() => updateQuantity(item.id, item.quantity - 1)}
                        disabled={item.quantity <= 1}
                        aria-label="Decrease quantity"
                      >
                        –
                      </button>
                      <span className="qty-display" aria-label="Current quantity">
                        {item.quantity}
                      </span>
                      <button
                        type="button"
                        className="qty-btn"
                        onClick={() => updateQuantity(item.id, item.quantity + 1)}
                        disabled={isAtMaxStock}
                        aria-label="Increase quantity"
                        title={isAtMaxStock ? "Maximum available stock reached" : "Increase quantity"}
                      >
                        +
                      </button>
                    </div>

                    {isAtMaxStock && (
                      <span className="qty-max-badge">Max Stock</span>
                    )}

                    <button
                      type="button"
                      className="cart-item-remove-btn"
                      onClick={() => removeFromCart(item.id)}
                    >
                      Remove
                    </button>
                  </div>

                  {/* Line Total */}
                  <div className="cart-item-total">
                    <span className="cart-item-line-price">{formatCurrency(item.price * item.quantity, item.currency)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Order Summary Sidebar */}
        <aside className="cart-summary-sidebar">
          <div className="summary-card">
            <h2 className="summary-title">Order Summary</h2>

            <div className="summary-row">
              <span className="summary-label">Items Subtotal</span>
              <span className="summary-value">{formatCurrency(subtotal)}</span>
            </div>

            <div className="summary-row">
              <span className="summary-label">Delivery Fee</span>
              <span className="summary-value">
                {deliveryFee === 0 ? (
                  <span className="free-shipping-tag">Free Delivery</span>
                ) : (
                  formatCurrency(deliveryFee)
                )}
              </span>
            </div>

            {subtotal < 999 && (
              <p className="free-shipping-hint">
                Add <strong>{formatCurrency(999 - subtotal)}</strong> more to unlock Free Delivery!
              </p>
            )}

            <div className="summary-divider"></div>

            <div className="summary-row total-row">
              <span className="summary-total-label">Estimated Total</span>
              <span className="summary-total-value">{formatCurrency(totalAmount)}</span>
            </div>

            <button
              type="button"
              className="btn-checkout-preview"
              onClick={goToCheckout}
            >
              Proceed to Checkout →
            </button>

            <div className="security-notice">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              <span>Prices and live stock availability will be re-verified on the backend at checkout.</span>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
