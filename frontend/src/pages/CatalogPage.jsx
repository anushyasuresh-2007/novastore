import React, { useState, useEffect, useCallback } from "react";
import Hero from "../components/Hero";
import FilterBar from "../components/FilterBar";
import ProductCard from "../components/ProductCard";
import ProductDetailsModal from "../components/ProductDetailsModal";
import LoadingState from "../components/LoadingState";
import EmptyState from "../components/EmptyState";
import { fetchProducts, fetchCategories } from "../services/api";

export default function CatalogPage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter & Search states
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [sortBy, setSortBy] = useState("");

  // Modal state
  const [selectedProductId, setSelectedProductId] = useState(null);

  // Debounce search input by 300ms
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Load category list on mount
  useEffect(() => {
    let isMounted = true;
    async function loadCategories() {
      try {
        const catList = await fetchCategories();
        if (isMounted) setCategories(catList);
      } catch (err) {
        console.error("Error fetching categories:", err);
      }
    }
    loadCategories();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch products whenever filters or sort change
  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchProducts({
        search: debouncedSearch,
        category: selectedCategory,
        minPrice,
        maxPrice,
        sort: sortBy,
      });
      setProducts(data.products || []);
    } catch (err) {
      setError(err.message || "Failed to load products. Please check server connection.");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, selectedCategory, minPrice, maxPrice, sortBy]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const handlePriceChange = (min, max) => {
    setMinPrice(min);
    setMaxPrice(max);
  };

  const handleResetFilters = () => {
    setSearchTerm("");
    setDebouncedSearch("");
    setSelectedCategory("All");
    setMinPrice("");
    setMaxPrice("");
    setSortBy("");
  };

  const hasActiveFilters = Boolean(
    searchTerm.trim() ||
    selectedCategory !== "All" ||
    minPrice !== "" ||
    maxPrice !== "" ||
    sortBy !== ""
  );

  return (
    <main>
      <Hero />

      <div className="store-container">
        <FilterBar
          categories={categories}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          minPrice={minPrice}
          maxPrice={maxPrice}
          onPriceChange={handlePriceChange}
          sortBy={sortBy}
          onSortChange={setSortBy}
          onResetFilters={handleResetFilters}
          hasActiveFilters={hasActiveFilters}
        />

        {error && (
          <div className="error-banner" role="alert">
            <span><strong>Connection Notice:</strong> {error}</span>
            <button className="error-retry-btn" onClick={loadProducts}>
              Retry Query
            </button>
          </div>
        )}

        <div className="results-summary">
          <span>
            Showing <strong className="results-count">{products.length}</strong> {products.length === 1 ? "product" : "products"}
            {selectedCategory !== "All" ? ` in ${selectedCategory}` : ""}
            {debouncedSearch ? ` matching "${debouncedSearch}"` : ""}
          </span>
        </div>

        {loading ? (
          <LoadingState message="Fetching live catalog from backend..." />
        ) : products.length === 0 ? (
          <EmptyState
            title="No matching products"
            message="No products match your current search and filter criteria."
            onReset={hasActiveFilters ? handleResetFilters : undefined}
          />
        ) : (
          <div className="product-grid">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                onViewDetails={(p) => setSelectedProductId(p.id)}
              />
            ))}
          </div>
        )}
      </div>

      {selectedProductId && (
        <ProductDetailsModal
          productId={selectedProductId}
          onClose={() => setSelectedProductId(null)}
        />
      )}
    </main>
  );
}
