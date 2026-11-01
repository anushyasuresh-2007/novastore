import React, { useState } from "react";
import { useCart } from "../context/CartContext";

export default function OrderConfirmationPage() {
  const { confirmedOrder, goToCatalog } = useCart();
  const [copied, setCopied] = useState(false);

  if (!confirmedOrder) {
    return (
      <main className="confirmation-page-container">
        <div className="cart-empty-state">
          <h2 className="cart-empty-title">No Recent Order Found</h2>
          <p className="cart-empty-subtitle">
            You do not have any active order confirmation in this session.
          </p>
          <button
            type="button"
            className="btn-continue-shopping"
            onClick={goToCatalog}
          >
            ← Return to Store
          </button>
        </div>
      </main>
    );
  }

  const handleCopyReference = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(confirmedOrder.order_reference);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formattedDate = confirmedOrder.created_at
    ? new Date(confirmedOrder.created_at).toLocaleString("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : new Date().toLocaleString();

  return (
    <main className="confirmation-page-container">
      <div className="confirmation-card">
        {/* Success Header */}
        <div className="confirmation-header">
          <div className="confirmation-check-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
          </div>
          <span className="confirmation-badge">Order Confirmed</span>
          <h1 className="confirmation-title">Thank You For Your Order!</h1>
          <p className="confirmation-subtitle">
            Your simulated order has been processed and saved in the database. A confirmation has been logged for <strong>{confirmedOrder.customer_email}</strong>.
          </p>
        </div>

        {/* Order Reference Box */}
        <div className="order-reference-box">
          <div className="reference-content">
            <span className="reference-label">Order Reference Number</span>
            <span className="reference-code">{confirmedOrder.order_reference}</span>
          </div>
          <button
            type="button"
            className="btn-copy-ref"
            onClick={handleCopyReference}
            title="Copy order reference to clipboard"
          >
            {copied ? (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copy Code</span>
              </>
            )}
          </button>
        </div>

        {/* Details Grid */}
        <div className="confirmation-grid">
          {/* Customer & Shipping Details */}
          <div className="detail-section">
            <h2 className="detail-section-title">Delivery Details</h2>
            <div className="detail-list">
              <div className="detail-row">
                <span className="detail-label">Customer Name:</span>
                <span className="detail-val">{confirmedOrder.customer_name}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Email:</span>
                <span className="detail-val">{confirmedOrder.customer_email}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Phone:</span>
                <span className="detail-val">{confirmedOrder.customer_phone}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Shipping Address:</span>
                <span className="detail-val">{confirmedOrder.delivery_address}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">City & Postal PIN:</span>
                <span className="detail-val">
                  {confirmedOrder.city}, {confirmedOrder.postal_code}
                </span>
              </div>
            </div>
          </div>

          {/* Order Status & Metadata */}
          <div className="detail-section">
            <h2 className="detail-section-title">Order Status</h2>
            <div className="detail-list">
              <div className="detail-row">
                <span className="detail-label">Status:</span>
                <span className="order-status-pill">{confirmedOrder.status}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Order Date:</span>
                <span className="detail-val">{formattedDate}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Payment Method:</span>
                <span className="detail-val">Simulated Checkout (Verified)</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Database Record:</span>
                <span className="detail-val">ID #{confirmedOrder.id}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Purchased Products Table */}
        <div className="confirmation-items-panel">
          <h2 className="detail-section-title" style={{ padding: "1.25rem 1.5rem 0" }}>
            Ordered Items
          </h2>

          <div className="confirmation-table">
            <div className="confirmation-table-header">
              <span>Item Description</span>
              <span style={{ textAlign: "center" }}>Unit Price</span>
              <span style={{ textAlign: "center" }}>Quantity</span>
              <span style={{ textAlign: "right" }}>Total</span>
            </div>

            <div className="confirmation-table-body">
              {(confirmedOrder.items || []).map((item) => (
                <div key={item.id} className="confirmation-table-row">
                  <div className="item-title-col">
                    <span className="item-name">{item.product_name}</span>
                    <span className="item-sku">Item ID: #{item.product_id}</span>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    ${Number(item.unit_price).toFixed(2)}
                  </div>
                  <div style={{ textAlign: "center" }}>
                    {item.quantity}
                  </div>
                  <div style={{ textAlign: "right", fontWeight: "600" }}>
                    ${Number(item.line_total).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Totals Summary */}
          <div className="confirmation-totals-box">
            <div className="summary-row">
              <span className="summary-label">Items Subtotal:</span>
              <span className="summary-value">${Number(confirmedOrder.subtotal).toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Delivery Charges:</span>
              <span className="summary-value">
                {Number(confirmedOrder.delivery_fee) === 0 ? "Free" : `$${Number(confirmedOrder.delivery_fee).toFixed(2)}`}
              </span>
            </div>
            <div className="summary-divider"></div>
            <div className="summary-row total-row">
              <span className="summary-total-label">Final Amount Paid:</span>
              <span className="summary-total-value">${Number(confirmedOrder.total_amount).toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="confirmation-footer-actions">
          <button
            type="button"
            className="btn-print-receipt"
            onClick={() => window.print()}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 6 2 18 2 18 9"></polyline>
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
              <rect x="6" y="14" width="12" height="8"></rect>
            </svg>
            <span>Print Receipt</span>
          </button>

          <button
            type="button"
            className="btn-continue-shopping"
            onClick={goToCatalog}
          >
            Continue Shopping →
          </button>
        </div>
      </div>
    </main>
  );
}
