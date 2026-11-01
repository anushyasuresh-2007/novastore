import React, { useState } from "react";

export default function ProductCard({ product, onViewDetails }) {
  const [imageError, setImageError] = useState(false);

  const fallbackImage = "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80";

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
          <span className="product-price">${Number(product.price).toFixed(2)}</span>
          {getStockBadge(product.stock_quantity)}
        </div>

        <div className="product-card-actions">
          <button
            type="button"
            className="btn-view-details"
            onClick={() => onViewDetails(product)}
          >
            Product Details
          </button>
          <button
            type="button"
            className="btn-add-cart-preview"
            title="Cart operations will be enabled in Phase 5"
            disabled={product.stock_quantity <= 0}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
          </button>
        </div>
      </div>
    </article>
  );
}
