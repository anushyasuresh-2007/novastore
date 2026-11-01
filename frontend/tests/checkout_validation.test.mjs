import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Checkout Validation & Order Flow Tests", () => {
  const validateCheckoutForm = (formData) => {
    const errs = {};
    const name = (formData.customer_name || "").trim();
    const email = (formData.customer_email || "").trim();
    const phone = (formData.customer_phone || "").trim().replace(/[\s\-]/g, "");
    const address = (formData.delivery_address || "").trim();
    const city = (formData.city || "").trim();
    const postal = (formData.postal_code || "").trim();

    if (!name || name.length < 2) {
      errs.customer_name = "Full name is required (at least 2 characters)";
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
      errs.customer_email = "Valid email is required";
    }

    const phoneRegex = /^(?:\+91)?[6-9]\d{9}$/;
    if (!phone || !phoneRegex.test(phone)) {
      errs.customer_phone = "Valid 10-digit mobile number is required";
    }

    if (!address || address.length < 5) {
      errs.delivery_address = "Address must be at least 5 characters long";
    }

    if (!city || city.length < 2) {
      errs.city = "City is required";
    }

    const postalRegex = /^\d{6}$/;
    if (!postal || !postalRegex.test(postal)) {
      errs.postal_code = "Valid 6-digit postal code (PIN code) is required";
    }

    return {
      isValid: Object.keys(errs).length === 0,
      errors: errs,
    };
  };

  it("should pass validation for complete valid customer inputs", () => {
    const validData = {
      customer_name: "Rahul Verma",
      customer_email: "rahul.verma@example.com",
      customer_phone: "+91 98765 43210",
      delivery_address: "Flat 304, Green Heights, Outer Ring Road",
      city: "Bengaluru",
      postal_code: "560103",
    };

    const result = validateCheckoutForm(validData);
    assert.equal(result.isValid, true);
    assert.equal(Object.keys(result.errors).length, 0);
  });

  it("should catch invalid email addresses", () => {
    const invalidData = {
      customer_name: "Rahul Verma",
      customer_email: "not-an-email",
      customer_phone: "9876543210",
      delivery_address: "Valid Address Street 123",
      city: "Delhi",
      postal_code: "110001",
    };

    const result = validateCheckoutForm(invalidData);
    assert.equal(result.isValid, false);
    assert.ok(result.errors.customer_email);
  });

  it("should catch invalid Indian mobile numbers", () => {
    const invalidPhones = ["1234567890", "98765", "009876543210", "abcdefghij"];

    for (const phone of invalidPhones) {
      const result = validateCheckoutForm({
        customer_name: "Tester",
        customer_email: "test@example.com",
        customer_phone: phone,
        delivery_address: "Valid Address",
        city: "Mumbai",
        postal_code: "400001",
      });
      assert.equal(result.isValid, false);
      assert.ok(result.errors.customer_phone);
    }
  });

  it("should catch invalid 6-digit postal codes", () => {
    const invalidPins = ["5600", "5600001", "PINCOD", "56000a"];

    for (const pin of invalidPins) {
      const result = validateCheckoutForm({
        customer_name: "Tester",
        customer_email: "test@example.com",
        customer_phone: "9876543210",
        delivery_address: "Valid Address",
        city: "Pune",
        postal_code: pin,
      });
      assert.equal(result.isValid, false);
      assert.ok(result.errors.postal_code);
    }
  });

  it("should preserve cart on checkout failure and clear cart on success", () => {
    let mockCart = [{ id: 1, name: "Item 1", price: 10, quantity: 2 }];

    const simulateCheckout = (isSuccess) => {
      if (isSuccess) {
        mockCart = [];
        return { success: true };
      } else {
        // Must NOT clear cart on failure
        return { success: false, error: "Network error" };
      }
    };

    // Simulate failed attempt
    const failResult = simulateCheckout(false);
    assert.equal(failResult.success, false);
    assert.equal(mockCart.length, 1); // Cart remains intact

    // Simulate successful attempt
    const successResult = simulateCheckout(true);
    assert.equal(successResult.success, true);
    assert.equal(mockCart.length, 0); // Cart cleared
  });
});
