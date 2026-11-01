import React, { useState } from "react";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { useCart } from "../../context/CartContext";

export default function AdminLoginPage() {
  const { login } = useAdminAuth();
  const { setCurrentView } = useCart();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError("Please enter both username/email and password.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await login(identifier.trim(), password);
    } catch (err) {
      setError(err.message || "Invalid administrator credentials. Access denied.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-login-wrapper">
      <div className="admin-login-card">
        <div className="admin-login-header">
          <div className="admin-login-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
          </div>
          <h2>Novastore Admin</h2>
          <p>Sign in to manage catalogue products, orders, and store metrics.</p>
        </div>

        {error && (
          <div className="admin-login-error" role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form className="admin-login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="admin-identifier">Username or Email</label>
            <input
              id="admin-identifier"
              type="text"
              className="admin-input"
              placeholder="e.g. admin or admin@novastore.com"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              disabled={loading}
              autoFocus
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="admin-password">Password</label>
            <input
              id="admin-password"
              type="password"
              className="admin-input"
              placeholder="Enter secure password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <button
            type="submit"
            className="admin-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="spinner-text">
                <span className="button-spinner"></span>
                Authenticating...
              </span>
            ) : (
              "Sign In to Dashboard"
            )}
          </button>
        </form>

        <div className="admin-login-footer">
          <button
            type="button"
            className="admin-back-store-btn"
            onClick={() => setCurrentView("catalog")}
          >
            ← Back to Customer Storefront
          </button>
        </div>
      </div>
    </div>
  );
}
