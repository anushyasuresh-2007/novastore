import React from "react";

export default function EmptyState({
  title = "No products found",
  message = "Try clearing search keywords or resetting price and category filters.",
  onReset,
}) {
  return (
    <div className="state-container">
      <div className="empty-state-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          <line x1="8" y1="11" x2="14" y2="11"></line>
        </svg>
      </div>
      <h3 className="state-title">{title}</h3>
      <p className="state-text">{message}</p>
      {onReset && (
        <button
          type="button"
          className="price-apply-btn"
          onClick={onReset}
        >
          Reset All Filters
        </button>
      )}
    </div>
  );
}
