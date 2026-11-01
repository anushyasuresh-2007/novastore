import React, { useState } from "react";

export default function FilterBar({
  categories = [],
  selectedCategory = "All",
  onSelectCategory,
  searchTerm = "",
  onSearchChange,
  minPrice = "",
  maxPrice = "",
  onPriceChange,
  sortBy = "",
  onSortChange,
  onResetFilters,
  hasActiveFilters = false,
}) {
  const [localMin, setLocalMin] = useState(minPrice);
  const [localMax, setLocalMax] = useState(maxPrice);

  const handlePriceSubmit = (e) => {
    e.preventDefault();
    onPriceChange(localMin, localMax);
  };

  const handleReset = () => {
    setLocalMin("");
    setLocalMax("");
    onResetFilters();
  };

  return (
    <div className="toolbar-card">
      {/* Top Row: Search and Sort */}
      <div className="toolbar-top-row">
        <div className="search-box-wrapper">
          <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="Search products by title or keyword..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        <div className="sort-select-wrapper">
          <label htmlFor="sort-dropdown" className="sort-label">Sort By:</label>
          <select
            id="sort-dropdown"
            className="sort-select"
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value)}
          >
            <option value="">Featured</option>
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="name_asc">Name: A to Z</option>
            <option value="name_desc">Name: Z to A</option>
          </select>
        </div>
      </div>

      {/* Bottom Row: Category Chips and Price Filter */}
      <div className="toolbar-bottom-row">
        <div className="category-chips">
          <button
            type="button"
            className={`chip-btn ${selectedCategory === "All" ? "active" : ""}`}
            onClick={() => onSelectCategory("All")}
          >
            All Products
          </button>
          {categories.map((cat) => (
            <button
              key={cat.name}
              type="button"
              className={`chip-btn ${selectedCategory.toLowerCase() === cat.name.toLowerCase() ? "active" : ""}`}
              onClick={() => onSelectCategory(cat.name)}
            >
              {cat.name} ({cat.count})
            </button>
          ))}
        </div>

        <form className="price-filter-group" onSubmit={handlePriceSubmit}>
          <div className="price-input-wrapper">
            <span className="currency-symbol">$</span>
            <input
              type="number"
              min="0"
              step="any"
              placeholder="Min"
              className="price-input"
              value={localMin}
              onChange={(e) => setLocalMin(e.target.value)}
            />
          </div>
          <span style={{ color: "var(--gray-400)" }}>–</span>
          <div className="price-input-wrapper">
            <span className="currency-symbol">$</span>
            <input
              type="number"
              min="0"
              step="any"
              placeholder="Max"
              className="price-input"
              value={localMax}
              onChange={(e) => setLocalMax(e.target.value)}
            />
          </div>
          <button type="submit" className="price-apply-btn">
            Apply
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              className="reset-filters-btn"
              onClick={handleReset}
            >
              Clear All
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
