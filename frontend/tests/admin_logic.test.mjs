import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Admin Dashboard Frontend Logic Tests", () => {
  // 1. Product Form Validation Logic
  const validateProductForm = (formData) => {
    const errors = {};
    if (!formData.name || formData.name.trim().length < 2) {
      errors.name = "Product name must be at least 2 characters long.";
    }
    if (!formData.description || formData.description.trim().length < 5) {
      errors.description = "Product description must be at least 5 characters long.";
    }
    if (!formData.category || !formData.category.trim()) {
      errors.category = "Please select or enter a category.";
    }
    const priceNum = parseFloat(formData.price);
    if (isNaN(priceNum) || priceNum < 0) {
      errors.price = "Price must be a valid non-negative number.";
    }
    const stockNum = parseInt(formData.stock_quantity, 10);
    if (isNaN(stockNum) || stockNum < 0 || String(formData.stock_quantity).includes(".")) {
      errors.stock_quantity = "Stock quantity must be a non-negative integer.";
    }
    return {
      isValid: Object.keys(errors).length === 0,
      errors,
    };
  };

  it("should validate complete valid product form data", () => {
    const validData = {
      name: "Ergonomic Mechanical Keyboard",
      description: "Tactile mechanical switches with wireless connectivity.",
      category: "Electronics",
      price: "89.99",
      stock_quantity: "25",
    };
    const res = validateProductForm(validData);
    assert.equal(res.isValid, true);
    assert.equal(Object.keys(res.errors).length, 0);
  });

  it("should reject short product name and short description", () => {
    const invalidData = {
      name: "A",
      description: "Tiny",
      category: "Electronics",
      price: "10.00",
      stock_quantity: "5",
    };
    const res = validateProductForm(invalidData);
    assert.equal(res.isValid, false);
    assert.ok(res.errors.name);
    assert.ok(res.errors.description);
  });

  it("should reject negative prices and decimal stock numbers", () => {
    const invalidData = {
      name: "Valid Product Title",
      description: "Valid detailed product description text.",
      category: "Audio",
      price: "-15.50",
      stock_quantity: "4.5",
    };
    const res = validateProductForm(invalidData);
    assert.equal(res.isValid, false);
    assert.ok(res.errors.price);
    assert.ok(res.errors.stock_quantity);
  });

  // 2. Controlled Order Status Validation
  const VALID_ORDER_STATUSES = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED"];
  const isValidOrderStatus = (status) => {
    return typeof status === "string" && VALID_ORDER_STATUSES.includes(status.trim().toUpperCase());
  };

  it("should accept valid controlled order statuses", () => {
    for (const status of VALID_ORDER_STATUSES) {
      assert.equal(isValidOrderStatus(status), true);
    }
  });

  it("should reject invalid order statuses", () => {
    const invalidStatuses = ["UNKNOWN", "REFUNDED", "RETURNED", "", null, 123];
    for (const status of invalidStatuses) {
      assert.equal(isValidOrderStatus(status), false);
    }
  });

  // State machine transition validator
  const ALLOWED_ORDER_STATUS_TRANSITIONS = {
    PENDING: ["PENDING", "CONFIRMED", "CANCELLED"],
    CONFIRMED: ["CONFIRMED", "SHIPPED", "CANCELLED"],
    SHIPPED: ["SHIPPED", "DELIVERED", "CANCELLED"],
    DELIVERED: ["DELIVERED"],
    CANCELLED: ["CANCELLED"],
  };

  const isAllowedStatusTransition = (currentStatus, targetStatus) => {
    const current = String(currentStatus || "").trim().toUpperCase();
    const target = String(targetStatus || "").trim().toUpperCase();
    const allowed = ALLOWED_ORDER_STATUS_TRANSITIONS[current];
    return Boolean(allowed && allowed.includes(target));
  };

  it("should allow valid forward status transitions", () => {
    assert.equal(isAllowedStatusTransition("PENDING", "CONFIRMED"), true);
    assert.equal(isAllowedStatusTransition("CONFIRMED", "SHIPPED"), true);
    assert.equal(isAllowedStatusTransition("SHIPPED", "DELIVERED"), true);
    assert.equal(isAllowedStatusTransition("CONFIRMED", "CANCELLED"), true);
    assert.equal(isAllowedStatusTransition("SHIPPED", "CANCELLED"), true);
  });

  it("should reject invalid backwards or terminal status transitions", () => {
    assert.equal(isAllowedStatusTransition("DELIVERED", "PENDING"), false);
    assert.equal(isAllowedStatusTransition("DELIVERED", "SHIPPED"), false);
    assert.equal(isAllowedStatusTransition("DELIVERED", "CANCELLED"), false);
    assert.equal(isAllowedStatusTransition("CANCELLED", "CONFIRMED"), false);
    assert.equal(isAllowedStatusTransition("CANCELLED", "SHIPPED"), false);
    assert.equal(isAllowedStatusTransition("CONFIRMED", "PENDING"), false);
  });

  it("should allow idempotent status updates", () => {
    assert.equal(isAllowedStatusTransition("DELIVERED", "DELIVERED"), true);
    assert.equal(isAllowedStatusTransition("CANCELLED", "CANCELLED"), true);
    assert.equal(isAllowedStatusTransition("CONFIRMED", "CONFIRMED"), true);
  });

  // 3. Authorization Header Construction
  const buildAuthHeader = (token) => {
    if (!token) return {};
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  };

  it("should format bearer authorization header correctly", () => {
    const header = buildAuthHeader("my-signed-admin-token-123");
    assert.equal(header.Authorization, "Bearer my-signed-admin-token-123");
    assert.equal(header["Content-Type"], "application/json");
  });

  it("should return empty object when no token is present", () => {
    const header = buildAuthHeader(null);
    assert.deepEqual(header, {});
  });

  // 4. Quick Stock Quantity Adjustment
  const calculateQuickStock = (currentStock, delta) => {
    return Math.max(0, (parseInt(currentStock, 10) || 0) + delta);
  };

  it("should increment and decrement stock safely without dropping below zero", () => {
    assert.equal(calculateQuickStock(10, 1), 11);
    assert.equal(calculateQuickStock(10, -1), 9);
    assert.equal(calculateQuickStock(0, -1), 0);
    assert.equal(calculateQuickStock(1, -5), 0);
  });
});
