/**
 * Unified currency formatting utility for Novastore.
 * Supports INR (₹) with standard Indian numbering system (e.g. ₹6,999, ₹74,999)
 * and USD ($) for historical order preservation (e.g. $94.99).
 */

export function formatCurrency(amount, currency = "INR") {
  const numeric = Number(amount) || 0;
  const curr = String(currency || "INR").toUpperCase();

  if (curr === "USD") {
    return `$${numeric.toFixed(2)}`;
  }

  // Format whole integer INR amounts without decimals; format fractions with 2 decimals
  const isWhole = Number.isInteger(numeric) || numeric % 1 === 0;
  const formatted = numeric.toLocaleString("en-IN", {
    minimumFractionDigits: isWhole ? 0 : 2,
    maximumFractionDigits: 2,
  });

  return `₹${formatted}`;
}

export default formatCurrency;
