import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Frontend API Client Tests", () => {
  const buildProductQueryUrl = (params = {}, base = "/api") => {
    const query = new URLSearchParams();
    if (params.search && params.search.trim()) query.set("search", params.search.trim());
    if (params.category && params.category.trim() && params.category !== "All") {
      query.set("category", params.category.trim());
    }
    if (params.minPrice !== "" && params.minPrice !== null && params.minPrice !== undefined) {
      query.set("min_price", params.minPrice);
    }
    if (params.maxPrice !== "" && params.maxPrice !== null && params.maxPrice !== undefined) {
      query.set("max_price", params.maxPrice);
    }
    if (params.sort && params.sort.trim()) query.set("sort", params.sort.trim());

    return `${base}/products${query.toString() ? `?${query.toString()}` : ""}`;
  };

  it("should construct query URL with search and sorting", () => {
    const url = buildProductQueryUrl({ search: "Keyboard", sort: "price_asc" });
    assert.equal(url, "/api/products?search=Keyboard&sort=price_asc");
  });

  it("should omit 'All' category from query string", () => {
    const url = buildProductQueryUrl({ category: "All" });
    assert.equal(url, "/api/products");
  });

  it("should include price bounds and category in query string", () => {
    const url = buildProductQueryUrl({
      category: "Audio",
      minPrice: "50",
      maxPrice: "200",
      sort: "name_desc",
    });
    assert.equal(
      url,
      "/api/products?category=Audio&min_price=50&max_price=200&sort=name_desc"
    );
  });

  it("should construct query URL for new Photography category", () => {
    const url = buildProductQueryUrl({ category: "Photography", sort: "price_desc" });
    assert.equal(url, "/api/products?category=Photography&sort=price_desc");
  });

  it("should support search within Photography category", () => {
    const url = buildProductQueryUrl({
      search: "Camera",
      category: "Photography",
      minPrice: "100",
    });
    assert.equal(url, "/api/products?search=Camera&category=Photography&min_price=100");
  });
});

