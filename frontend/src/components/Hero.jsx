import React from "react";

export default function Hero() {
  return (
    <section className="hero-section">
      <div className="hero-container">
        <div className="hero-badge">
          <span>✨</span> Official Online Shopping Store
        </div>
        <h1 className="hero-title">
          Curated Tech & Modern Lifestyle Essentials
        </h1>
        <p className="hero-subtitle">
          Discover top-tier electronics, professional audio, ergonomic gear, and smart home accessories directly from our verified inventory.
        </p>
        <div className="hero-perks">
          <div className="hero-perk-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="1" y="3" width="15" height="13"></rect>
              <polygon points="16 8 20 8 23 11 23 16 16 16 8"></polygon>
              <circle cx="5.5" cy="18.5" r="2.5"></circle>
              <circle cx="18.5" cy="18.5" r="2.5"></circle>
            </svg>
            <span>Free delivery on orders above ₹999</span>
          </div>
        </div>
      </div>
    </section>
  );
}
