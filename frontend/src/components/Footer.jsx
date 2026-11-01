import React from "react";

export default function Footer() {
  return (
    <footer className="footer">
      <p>© {new Date().getFullYear()} Novastore Online Store. Built with React & Python Flask.</p>
    </footer>
  );
}
