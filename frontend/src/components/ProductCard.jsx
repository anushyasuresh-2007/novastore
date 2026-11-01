import React, { useState } from "react";
import { useCart } from "../context/CartContext";
import { formatCurrency } from "../utils/currency";

export default function ProductCard({ product, onViewDetails }) {
  const { addToCart } = useCart();
  const [imageError, setImageError] = useState(false);
  const [justAdded, setJustAdded] = useState(false);

  const fallbackImage = "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80";

  const isOutOfStock = product.stock_quantity <= 0;

  const handleAddToCart = (e) => {
    e.stopPropagation();
    if (isOutOfStock) return;

    const res = addToCart(product, 1);
    if (res.success) {
      setJustAdded(true);
      setTimeout(() => setJustAdded(false), 900);
    }
  };

  const getStockBadge = (stock) => {
    if (stock <= 0) {
      return <span className="stock-pill stock-out">Out of Stock</span>;
    }
    if (stock <= 15) {
      return <span className="stock-pill stock-low">Only {stock} Left</span>;
    }
    return <span className="stock-pill stock-in">In Stock ({stock})</span>;
  };

  return (
    <article className="product-card" id={`product-${product.id}`}>
      <div
        className="product-image-container"
        onClick={() => onViewDetails(product)}
        title={`View details for ${product.name}`}
      >
        <img
          src={imageError || !product.image_path ? fallbackImage : product.image_path}
          alt={product.name}
          className="product-image"
          loading="lazy"
          onError={() => setImageError(true)}
        />
        <span className="category-tag">{product.category}</span>
      </div>

      <div className="product-body">
        <h3
          className="product-title"
          onClick={() => onViewDetails(product)}
          title={product.name}
        >
          {product.name}
        </h3>

        <p className="product-description">
          {product.description}
        </p>

        <div className="product-meta-row">
          <span className="product-price">{formatCurrency(product.price, product.currency)}</span>
          {getStockBadge(product.stock_quantity)}
        </div>

        <div className="product-card-actions">
          <button
            type="button"
            className="btn-view-details"
            onClick={() => onViewDetails(product)}
          >
            Details
          </button>
          <button
            type="button"
            className={`btn-add-cart ${justAdded ? "btn-added" : ""}`}
            onClick={handleAddToCart}
            disabled={isOutOfStock}
            title={isOutOfStock ? "Out of Stock" : "Add 1 unit to cart"}
          >
            {justAdded ? (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Added!</span>
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="9" cy="21" r="1"></circle>
                  <circle cx="20" cy="21" r="1"></circle>
                  <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
                <span>Add to Cart</span>
              </>
            )}
          </button>
        </div>
      </div>
    </article>
  );
}
