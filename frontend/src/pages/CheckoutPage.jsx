import React, { useState } from "react";
import { useCart } from "../context/CartContext";
import { createOrder } from "../services/api";
import { formatCurrency } from "../utils/currency";

export default function CheckoutPage() {
  const {
    cartItems,
    subtotal,
    deliveryFee,
    totalAmount,
    clearCart,
    goToCart,
    goToConfirmation,
    goToCatalog,
  } = useCart();

  const [formData, setFormData] = useState({
    customer_name: "",
    customer_email: "",
    customer_phone: "",
    delivery_address: "",
    city: "",
    postal_code: "",
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);

  const fallbackImage = "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80";

  if (cartItems.length === 0) {
    return (
      <main className="checkout-page-container">
        <div className="cart-empty-state">
          <h2 className="cart-empty-title">Cannot Proceed to Checkout</h2>
          <p className="cart-empty-subtitle">
            Your shopping cart is currently empty. Please add items before checking out.
          </p>
          <button
            type="button"
            className="btn-continue-shopping"
            onClick={goToCatalog}
          >
            ← Explore Catalog
          </button>
        </div>
      </main>
    );
  }

  const validate = () => {
    const errs = {};
    const name = formData.customer_name.trim();
    const email = formData.customer_email.trim();
    const phone = formData.customer_phone.trim().replace(/[\s\-]/g, "");
    const address = formData.delivery_address.trim();
    const city = formData.city.trim();
    const postal = formData.postal_code.trim();

    if (!name) {
      errs.customer_name = "Full name is required";
    } else if (name.length < 2) {
      errs.customer_name = "Name must be at least 2 characters";
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) {
      errs.customer_email = "Email address is required";
    } else if (!emailRegex.test(email)) {
      errs.customer_email = "Please enter a valid email address (e.g. name@domain.com)";
    }

    // Indian phone format check: 10 digits starting with 6-9 (optional +91)
    const phoneRegex = /^(?:\+91)?[6-9]\d{9}$/;
    if (!phone) {
      errs.customer_phone = "Phone number is required";
    } else if (!phoneRegex.test(phone)) {
      errs.customer_phone = "Please enter a valid 10-digit mobile number (e.g. 9876543210)";
    }

    if (!address) {
      errs.delivery_address = "Delivery address is required";
    } else if (address.length < 5) {
      errs.delivery_address = "Address must be at least 5 characters long";
    }

    if (!city) {
      errs.city = "City is required";
    } else if (city.length < 2) {
      errs.city = "City must be at least 2 characters";
    }

    // Indian PIN code format: exactly 6 digits
    const postalRegex = /^\d{6}$/;
    if (!postal) {
      errs.postal_code = "PIN / Postal code is required";
    } else if (!postalRegex.test(postal)) {
      errs.postal_code = "Please enter a valid 6-digit postal code (PIN code)";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear field-specific error as user types
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const orderPayload = {
        customer_name: formData.customer_name.trim(),
        customer_email: formData.customer_email.trim(),
        customer_phone: formData.customer_phone.trim(),
        delivery_address: formData.delivery_address.trim(),
        city: formData.city.trim(),
        postal_code: formData.postal_code.trim(),
        items: cartItems.map((item) => ({
          product_id: item.id,
          quantity: item.quantity,
        })),
      };

      const result = await createOrder(orderPayload);

      // Order succeeded: clear cart and redirect to confirmation
      clearCart();
      goToConfirmation(result.order);
    } catch (err) {
      setApiError(err.message || "Failed to place order. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="checkout-page-container">
      <div className="checkout-header-row">
        <div>
          <h1 className="checkout-title">Checkout & Shipping</h1>
          <p className="checkout-subtitle">
            Provide your delivery details to complete your simulated order.
          </p>
        </div>
        <button
          type="button"
          className="btn-text-secondary"
          onClick={goToCart}
        >
          ← Return to Cart
        </button>
      </div>

      {apiError && (
        <div className="error-banner" role="alert" style={{ marginBottom: "2rem" }}>
          <span><strong>Order Processing Notice:</strong> {apiError}</span>
        </div>
      )}

      <div className="checkout-layout-grid">
        {/* Shipping Information Form */}
        <div className="checkout-form-panel">
          <form onSubmit={handleSubmit} noValidate>
            <h2 className="form-section-heading">1. Customer Information</h2>

            <div className="form-grid">
              {/* Full Name */}
              <div className="form-group full-width">
                <label htmlFor="customer_name" className="form-label">
                  Full Name <span className="required-star">*</span>
                </label>
                <input
                  id="customer_name"
                  name="customer_name"
                  type="text"
                  placeholder="e.g. Rohan Sharma"
                  className={`form-input ${errors.customer_name ? "input-error" : ""}`}
                  value={formData.customer_name}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
                {errors.customer_name && (
                  <span className="field-error-msg">{errors.customer_name}</span>
                )}
              </div>

              {/* Email Address */}
              <div className="form-group">
                <label htmlFor="customer_email" className="form-label">
                  Email Address <span className="required-star">*</span>
                </label>
                <input
                  id="customer_email"
                  name="customer_email"
                  type="email"
                  placeholder="name@example.com"
                  className={`form-input ${errors.customer_email ? "input-error" : ""}`}
                  value={formData.customer_email}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
                {errors.customer_email && (
                  <span className="field-error-msg">{errors.customer_email}</span>
                )}
              </div>

              {/* Phone Number */}
              <div className="form-group">
                <label htmlFor="customer_phone" className="form-label">
                  Phone Number <span className="required-star">*</span>
                </label>
                <input
                  id="customer_phone"
                  name="customer_phone"
                  type="tel"
                  placeholder="10-digit mobile (e.g. 9876543210)"
                  className={`form-input ${errors.customer_phone ? "input-error" : ""}`}
                  value={formData.customer_phone}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
                {errors.customer_phone && (
                  <span className="field-error-msg">{errors.customer_phone}</span>
                )}
              </div>
            </div>

            <h2 className="form-section-heading" style={{ marginTop: "2rem" }}>
              2. Delivery Address
            </h2>

            <div className="form-grid">
              {/* Address */}
              <div className="form-group full-width">
                <label htmlFor="delivery_address" className="form-label">
                  Street Address / House No. <span className="required-star">*</span>
                </label>
                <input
                  id="delivery_address"
                  name="delivery_address"
                  type="text"
                  placeholder="Flat / House No., Apartment, Street name"
                  className={`form-input ${errors.delivery_address ? "input-error" : ""}`}
                  value={formData.delivery_address}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
                {errors.delivery_address && (
                  <span className="field-error-msg">{errors.delivery_address}</span>
                )}
              </div>

              {/* City */}
              <div className="form-group">
                <label htmlFor="city" className="form-label">
                  City <span className="required-star">*</span>
                </label>
                <input
                  id="city"
                  name="city"
                  type="text"
                  placeholder="e.g. Bengaluru, Mumbai, Delhi"
                  className={`form-input ${errors.city ? "input-error" : ""}`}
                  value={formData.city}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
                {errors.city && (
                  <span className="field-error-msg">{errors.city}</span>
                )}
              </div>

              {/* Postal Code */}
              <div className="form-group">
                <label htmlFor="postal_code" className="form-label">
                  Postal / PIN Code (6 digits) <span className="required-star">*</span>
                </label>
                <input
                  id="postal_code"
                  name="postal_code"
                  type="text"
                  maxLength="6"
                  placeholder="e.g. 560001"
                  className={`form-input ${errors.postal_code ? "input-error" : ""}`}
                  value={formData.postal_code}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
                {errors.postal_code && (
                  <span className="field-error-msg">{errors.postal_code}</span>
                )}
              </div>
            </div>

            <div className="simulated-payment-box">
              <div className="simulated-payment-header">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                  <line x1="1" y1="10" x2="23" y2="10"></line>
                </svg>
                <span>Simulated Checkout (No Real Payment Required)</span>
              </div>
              <p className="simulated-payment-desc">
                This transaction will simulate verified order placement. Products and pricing will be recalculated and deducted atomically from the backend SQLite database upon clicking Place Order.
              </p>
            </div>

            <button
              type="submit"
              className="btn-place-order"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="btn-spinner"></span>
                  <span>Verifying & Placing Order...</span>
                </>
              ) : (
                `Place Order • ${formatCurrency(totalAmount)}`
              )}
            </button>
          </form>
        </div>

        {/* Order Summary Sidebar */}
        <aside className="checkout-summary-sidebar">
          <div className="summary-card">
            <h2 className="summary-title">Order Items ({cartItems.length})</h2>

            <div className="checkout-items-list">
              {cartItems.map((item) => (
                <div key={item.id} className="checkout-item-compact">
                  <img
                    src={item.image_path || fallbackImage}
                    alt={item.name}
                    className="checkout-item-thumb"
                    onError={(e) => { e.target.src = fallbackImage; }}
                  />
                  <div className="checkout-item-details">
                    <span className="checkout-item-title">{item.name}</span>
                    <span className="checkout-item-sub">
                      Qty: {item.quantity} × {formatCurrency(item.price, item.currency)}
                    </span>
                  </div>
                  <span className="checkout-item-total">
                    {formatCurrency(item.price * item.quantity, item.currency)}
                  </span>
                </div>
              ))}
            </div>

            <div className="summary-divider"></div>

            <div className="summary-row">
              <span className="summary-label">Items Subtotal</span>
              <span className="summary-value">{formatCurrency(subtotal)}</span>
            </div>

            <div className="summary-row">
              <span className="summary-label">Delivery Fee</span>
              <span className="summary-value">
                {deliveryFee === 0 ? (
                  <span className="free-shipping-tag">Free</span>
                ) : (
                  formatCurrency(deliveryFee)
                )}
              </span>
            </div>

            <div className="summary-divider"></div>

            <div className="summary-row total-row">
              <span className="summary-total-label">Final Amount</span>
              <span className="summary-total-value">{formatCurrency(totalAmount)}</span>
            </div>

            <div className="security-notice">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
              <span>Bank-grade security: Database inventory and prices are re-verified upon submission.</span>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
