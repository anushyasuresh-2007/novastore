import React from "react";
import { useCart } from "../context/CartContext";

export default function Footer() {
  const { setCurrentView } = useCart();

  return (
    <footer className="footer">
      <div className="footer-content">
        <p>© {new Date().getFullYear()} Novastore Online Store. Built with React & Python Flask.</p>
        <button
          type="button"
          className="footer-admin-link"
          onClick={() => setCurrentView("admin")}
        >
          🔒 Admin Portal
        </button>
      </div>
    </footer>
  );
}

