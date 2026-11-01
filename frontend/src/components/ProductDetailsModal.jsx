import React, { useEffect, useState } from "react";
import { fetchProductById } from "../services/api";

export default function ProductDetailsModal({ productId, onClose }) {
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadDetails() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchProductById(productId);
        if (isMounted) setProduct(data);
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    if (productId) {
      loadDetails();
    }

    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      isMounted = false;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [productId, onClose]);

  const fallbackImage = "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80";

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        {loading ? (
          <div className="state-container" style={{ minHeight: "340px" }}>
            <div className="spinner"></div>
            <p className="state-text">Loading item specifications...</p>
          </div>
        ) : error ? (
          <div className="state-container" style={{ minHeight: "340px" }}>
            <p className="state-title" style={{ color: "var(--danger-text)" }}>Error loading product</p>
            <p className="state-text">{error}</p>
          </div>
        ) : product ? (
          <div className="modal-grid">
            <div className="modal-image-wrapper">
              <img
                src={product.image_path || fallbackImage}
                alt={product.name}
                className="modal-image"
                onError={(e) => { e.target.src = fallbackImage; }}
              />
            </div>
            <div className="modal-info-pane">
              <span className="modal-category">{product.category}</span>
              <h2 className="modal-title">{product.name}</h2>

              <div className="modal-price-row">
                <span className="modal-price">${Number(product.price).toFixed(2)}</span>
                <span className={`stock-pill ${product.stock_quantity > 0 ? "stock-in" : "stock-out"}`}>
                  {product.stock_quantity > 0 ? `${product.stock_quantity} in stock` : "Out of stock"}
                </span>
              </div>

              <h4 className="modal-description-heading">Overview</h4>
              <p className="modal-description">{product.description}</p>

              <div className="modal-specs-list">
                <div className="modal-spec-item">
                  <span className="modal-spec-label">SKU / Item ID:</span>
                  <span className="modal-spec-val">NOV-{String(product.id).padStart(5, "0")}</span>
                </div>
                <div className="modal-spec-item">
                  <span className="modal-spec-label">Category:</span>
                  <span className="modal-spec-val">{product.category}</span>
                </div>
                <div className="modal-spec-item">
                  <span className="modal-spec-label">Availability:</span>
                  <span className="modal-spec-val">{product.stock_quantity > 0 ? "Ready to Dispatch" : "Temporarily Unavailable"}</span>
                </div>
              </div>

              <button
                type="button"
                className="btn-view-details"
                style={{ padding: "0.875rem", fontSize: "0.9375rem" }}
                disabled={product.stock_quantity <= 0}
                title="Full cart and purchasing is enabled in upcoming phases"
              >
                {product.stock_quantity > 0 ? "Add to Cart (Phase 5)" : "Out of Stock"}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
