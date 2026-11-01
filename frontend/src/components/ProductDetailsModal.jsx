import React, { useEffect, useState } from "react";
import { fetchProductById } from "../services/api";
import { useCart } from "../context/CartContext";
import { formatCurrency } from "../utils/currency";

export default function ProductDetailsModal({ productId, onClose }) {
  const { addToCart } = useCart();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [justAdded, setJustAdded] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function loadDetails() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchProductById(productId);
        if (isMounted) {
          setProduct(data);
          setQuantity(1);
        }
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

  const handleAddToCart = () => {
    if (!product || product.stock_quantity <= 0) return;

    const res = addToCart(product, quantity);
    if (res.success) {
      setJustAdded(true);
      setTimeout(() => setJustAdded(false), 1200);
    }
  };

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
                <span className="modal-price">{formatCurrency(product.price, product.currency)}</span>
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

              {product.stock_quantity > 0 ? (
                <div className="modal-actions-container">
                  <div className="modal-qty-selector">
                    <span className="modal-qty-label">Quantity:</span>
                    <div className="qty-stepper">
                      <button
                        type="button"
                        className="qty-btn"
                        onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                        disabled={quantity <= 1}
                      >
                        –
                      </button>
                      <span className="qty-display">{quantity}</span>
                      <button
                        type="button"
                        className="qty-btn"
                        onClick={() => setQuantity((q) => Math.min(product.stock_quantity, q + 1))}
                        disabled={quantity >= product.stock_quantity}
                      >
                        +
                      </button>
                    </div>
                  </div>

                  <button
                    type="button"
                    className={`btn-modal-add-cart ${justAdded ? "btn-added" : ""}`}
                    onClick={handleAddToCart}
                  >
                    {justAdded ? (
                      <>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span>Added to Cart!</span>
                      </>
                    ) : (
                      <>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="9" cy="21" r="1"></circle>
                          <circle cx="20" cy="21" r="1"></circle>
                          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                        </svg>
                        <span>Add {quantity} to Cart</span>
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="btn-modal-add-cart"
                  disabled
                  style={{ opacity: 0.6, cursor: "not-allowed" }}
                >
                  Currently Out of Stock
                </button>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
