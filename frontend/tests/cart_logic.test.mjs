import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

// Mock localStorage for headless Node environment
class MockLocalStorage {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return this.store[key] || null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

globalThis.localStorage = new MockLocalStorage();

describe("Shopping Cart Logic & State Tests", () => {
  let cartItems = [];

  const sampleProduct1 = {
    id: 1,
    name: "Ultra-Slim Wireless Mechanical Keyboard",
    price: 89.99,
    stock_quantity: 5,
    category: "Electronics",
  };

  const sampleProduct2 = {
    id: 2,
    name: "Precision Ergonomic Optical Mouse",
    price: 49.50,
    stock_quantity: 10,
    category: "Electronics",
  };

  const outOfStockProduct = {
    id: 3,
    name: "Sold Out Headphones",
    price: 199.99,
    stock_quantity: 0,
    category: "Audio",
  };

  const addToCart = (product, qty = 1) => {
    if (!product || product.stock_quantity <= 0) {
      return { success: false, message: "Out of stock" };
    }
    const existing = cartItems.find((item) => item.id === product.id);
    if (existing) {
      const newTotal = existing.quantity + qty;
      if (newTotal > product.stock_quantity) {
        existing.quantity = product.stock_quantity;
        return { success: true, capped: true, message: "Max stock reached" };
      }
      existing.quantity = newTotal;
      return { success: true, capped: false, message: "Quantity updated" };
    } else {
      if (qty > product.stock_quantity) {
        return { success: false, message: "Exceeds stock" };
      }
      cartItems.push({ ...product, quantity: qty });
      return { success: true, capped: false, message: "Added to cart" };
    }
  };

  const updateQuantity = (productId, newQty) => {
    const item = cartItems.find((i) => i.id === productId);
    if (!item) return;
    if (newQty < 1) return;
    if (newQty > item.stock_quantity) {
      item.quantity = item.stock_quantity;
    } else {
      item.quantity = newQty;
    }
  };

  const removeFromCart = (productId) => {
    cartItems = cartItems.filter((i) => i.id !== productId);
  };

  const clearCart = () => {
    cartItems = [];
  };

  const computeTotals = () => {
    const subtotal = cartItems.reduce((acc, i) => acc + i.price * i.quantity, 0);
    const deliveryFee = cartItems.length === 0 ? 0 : subtotal >= 100 ? 0 : 5.0;
    const totalAmount = subtotal + deliveryFee;
    return {
      subtotal: Number(subtotal.toFixed(2)),
      deliveryFee: Number(deliveryFee.toFixed(2)),
      totalAmount: Number(totalAmount.toFixed(2)),
    };
  };

  beforeEach(() => {
    cartItems = [];
    localStorage.clear();
  });

  it("should add in-stock product to cart", () => {
    const res = addToCart(sampleProduct1, 1);
    assert.equal(res.success, true);
    assert.equal(cartItems.length, 1);
    assert.equal(cartItems[0].name, sampleProduct1.name);
    assert.equal(cartItems[0].quantity, 1);
  });

  it("should reject adding an out-of-stock product", () => {
    const res = addToCart(outOfStockProduct, 1);
    assert.equal(res.success, false);
    assert.equal(cartItems.length, 0);
  });

  it("should enforce stock limits when adding more than available", () => {
    // Stock is 5
    addToCart(sampleProduct1, 3);
    assert.equal(cartItems[0].quantity, 3);

    // Adding 4 more would be 7, should be capped at 5
    const res = addToCart(sampleProduct1, 4);
    assert.equal(res.success, true);
    assert.equal(res.capped, true);
    assert.equal(cartItems[0].quantity, 5);
  });

  it("should allow quantity increment and decrement within bounds", () => {
    addToCart(sampleProduct2, 2);
    assert.equal(cartItems[0].quantity, 2);

    // Increase to 5
    updateQuantity(sampleProduct2.id, 5);
    assert.equal(cartItems[0].quantity, 5);

    // Decrease to 1
    updateQuantity(sampleProduct2.id, 1);
    assert.equal(cartItems[0].quantity, 1);

    // Cannot decrease below 1
    updateQuantity(sampleProduct2.id, 0);
    assert.equal(cartItems[0].quantity, 1);

    // Cannot increase beyond stock of 10
    updateQuantity(sampleProduct2.id, 99);
    assert.equal(cartItems[0].quantity, 10);
  });

  it("should calculate subtotal, delivery fee and totals correctly", () => {
    // Under $100: 1 mouse ($49.50) -> delivery fee is $5.00
    addToCart(sampleProduct2, 1);
    let totals = computeTotals();
    assert.equal(totals.subtotal, 49.50);
    assert.equal(totals.deliveryFee, 5.00);
    assert.equal(totals.totalAmount, 54.50);

    // Over $100: 1 keyboard ($89.99) + 1 mouse ($49.50) = $139.49 -> free delivery
    addToCart(sampleProduct1, 1);
    totals = computeTotals();
    assert.equal(totals.subtotal, 139.49);
    assert.equal(totals.deliveryFee, 0.00);
    assert.equal(totals.totalAmount, 139.49);
  });

  it("should remove individual items and clear cart", () => {
    addToCart(sampleProduct1, 1);
    addToCart(sampleProduct2, 1);
    assert.equal(cartItems.length, 2);

    removeFromCart(sampleProduct1.id);
    assert.equal(cartItems.length, 1);
    assert.equal(cartItems[0].id, sampleProduct2.id);

    clearCart();
    assert.equal(cartItems.length, 0);
    const totals = computeTotals();
    assert.equal(totals.subtotal, 0);
    assert.equal(totals.deliveryFee, 0);
    assert.equal(totals.totalAmount, 0);
  });

  it("should serialize and restore cart from localStorage", () => {
    addToCart(sampleProduct1, 2);
    localStorage.setItem("novastore_cart_items", JSON.stringify(cartItems));

    // Restore into fresh array
    const saved = JSON.parse(localStorage.getItem("novastore_cart_items"));
    assert.equal(Array.isArray(saved), true);
    assert.equal(saved.length, 1);
    assert.equal(saved[0].name, sampleProduct1.name);
    assert.equal(saved[0].quantity, 2);
  });
});
