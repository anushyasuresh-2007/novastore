import React from "react";
import { CartProvider, useCart } from "./context/CartContext";
import Navbar from "./components/Navbar";
import CatalogPage from "./pages/CatalogPage";
import CartPage from "./pages/CartPage";
import NotificationToast from "./components/NotificationToast";
import Footer from "./components/Footer";

function StoreContent() {
  const { currentView } = useCart();

  return (
    <div className="app-layout">
      <Navbar />
      {currentView === "cart" ? <CartPage /> : <CatalogPage />}
      <NotificationToast />
      <Footer />
    </div>
  );
}

function App() {
  return (
    <CartProvider>
      <StoreContent />
    </CartProvider>
  );
}

export default App;
