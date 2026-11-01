import React from "react";
import Navbar from "./components/Navbar";
import CatalogPage from "./pages/CatalogPage";
import Footer from "./components/Footer";

function App() {
  return (
    <div className="app-layout">
      <Navbar cartCount={0} />
      <CatalogPage />
      <Footer />
    </div>
  );
}

export default App;
