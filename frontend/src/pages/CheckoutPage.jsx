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
    state: "",
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

  const validateField = (name, value) => {
    const val = (value !== undefined ? value : formData[name] || "").trim();
    switch (name) {
      case "customer_name":
        if (!val) return "Full name is required";
        if (val.length < 2) return "Name must be at least 2 characters";
        return null;
      case "customer_email": {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!val) return "Email address is required";
        if (!emailRegex.test(val)) return "Please enter a valid email address (e.g. name@domain.com)";
        return null;
      }
      case "customer_phone": {
        const cleanPhone = val.replace(/[\s\-]/g, "");
        const phoneRegex = /^(?:\+91)?[6-9]\d{9}$/;
        if (!cleanPhone) return "Phone number is required";
        if (!phoneRegex.test(cleanPhone)) return "Please enter a valid 10-digit mobile number (e.g. 9876543210)";
        return null;
      }
      case "delivery_address":
        if (!val) return "Delivery address is required";
        if (val.length < 5) return "Address must be at least 5 characters long";
        return null;
      case "city":
        if (!val) return "City is required";
        if (val.length < 2) return "City must be at least 2 characters";
        return null;
      case "postal_code": {
        const postalRegex = /^\d{6}$/;
        if (!val) return "PIN / Postal code is required";
        if (!postalRegex.test(val)) return "Please enter a valid 6-digit postal code (PIN code)";
        return null;
      }
      default:
        return null;
    }
  };

  const validate = () => {
    const fields = ["customer_name", "customer_email", "customer_phone", "delivery_address", "city", "postal_code"];
    const errs = {};
    for (const field of fields) {
      const errorMsg = validateField(field, formData[field]);
      if (errorMsg) {
        errs[field] = errorMsg;
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    const errorMsg = validateField(name, value);
    if (errorMsg) {
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // If field already has an error, re-validate to clear or update as user types
    if (errors[name]) {
      const errorMsg = validateField(name, value);
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
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
      const formattedAddress = formData.state && formData.state.trim()
        ? `${formData.delivery_address.trim()}, ${formData.state.trim()}`
        : formData.delivery_address.trim();

      const orderPayload = {
        customer_name: formData.customer_name.trim(),
        customer_email: formData.customer_email.trim(),
        customer_phone: formData.customer_phone.trim(),
        delivery_address: formattedAddress,
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
          aria-label="Return to shopping cart"
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
                  autoComplete="name"
                  placeholder="e.g. Rohan Sharma"
                  className={`form-input ${errors.customer_name ? "input-error" : ""}`}
                  value={formData.customer_name}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={Boolean(errors.customer_name)}
                  aria-describedby={errors.customer_name ? "customer_name_error" : undefined}
                  disabled={isSubmitting}
                />
                {errors.customer_name && (
                  <span id="customer_name_error" className="field-error-msg" role="alert">
                    {errors.customer_name}
                  </span>
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
                  autoComplete="email"
                  placeholder="name@example.com"
                  className={`form-input ${errors.customer_email ? "input-error" : ""}`}
                  value={formData.customer_email}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={Boolean(errors.customer_email)}
                  aria-describedby={errors.customer_email ? "customer_email_error" : undefined}
                  disabled={isSubmitting}
                />
                {errors.customer_email && (
                  <span id="customer_email_error" className="field-error-msg" role="alert">
                    {errors.customer_email}
                  </span>
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
                  autoComplete="tel"
                  placeholder="10-digit mobile (e.g. 9876543210)"
                  className={`form-input ${errors.customer_phone ? "input-error" : ""}`}
                  value={formData.customer_phone}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={Boolean(errors.customer_phone)}
                  aria-describedby={errors.customer_phone ? "customer_phone_error" : undefined}
                  disabled={isSubmitting}
                />
                {errors.customer_phone && (
                  <span id="customer_phone_error" className="field-error-msg" role="alert">
                    {errors.customer_phone}
                  </span>
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
                  autoComplete="street-address"
                  placeholder="Flat / House No., Apartment, Street name"
                  className={`form-input ${errors.delivery_address ? "input-error" : ""}`}
                  value={formData.delivery_address}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={Boolean(errors.delivery_address)}
                  aria-describedby={errors.delivery_address ? "delivery_address_error" : undefined}
                  disabled={isSubmitting}
                />
                {errors.delivery_address && (
                  <span id="delivery_address_error" className="field-error-msg" role="alert">
                    {errors.delivery_address}
                  </span>
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
                  autoComplete="address-level2"
                  placeholder="e.g. Bengaluru, Mumbai, Delhi"
                  className={`form-input ${errors.city ? "input-error" : ""}`}
                  value={formData.city}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={Boolean(errors.city)}
                  aria-describedby={errors.city ? "city_error" : undefined}
                  disabled={isSubmitting}
                />
                {errors.city && (
                  <span id="city_error" className="field-error-msg" role="alert">
                    {errors.city}
                  </span>
                )}
              </div>

              {/* State */}
              <div className="form-group">
                <label htmlFor="state" className="form-label">
                  State / Province
                </label>
                <input
                  id="state"
                  name="state"
                  type="text"
                  autoComplete="address-level1"
                  placeholder="e.g. Karnataka, Maharashtra"
                  className="form-input"
                  value={formData.state}
                  onChange={handleChange}
                  disabled={isSubmitting}
                />
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
                  autoComplete="postal-code"
                  maxLength="6"
                  placeholder="e.g. 560001"
                  className={`form-input ${errors.postal_code ? "input-error" : ""}`}
                  value={formData.postal_code}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={Boolean(errors.postal_code)}
                  aria-describedby={errors.postal_code ? "postal_code_error" : undefined}
                  disabled={isSubmitting}
                />
                {errors.postal_code && (
                  <span id="postal_code_error" className="field-error-msg" role="alert">
                    {errors.postal_code}
                  </span>
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
