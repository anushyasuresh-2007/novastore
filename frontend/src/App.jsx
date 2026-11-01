import React from "react";
import { CartProvider, useCart } from "./context/CartContext";
import Navbar from "./components/Navbar";
import CatalogPage from "./pages/CatalogPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import OrderConfirmationPage from "./pages/OrderConfirmationPage";
import NotificationToast from "./components/NotificationToast";
import Footer from "./components/Footer";

function StoreContent() {
  const { currentView } = useCart();

  const renderCurrentView = () => {
    switch (currentView) {
      case "cart":
        return <CartPage />;
      case "checkout":
        return <CheckoutPage />;
      case "confirmation":
        return <OrderConfirmationPage />;
      case "catalog":
      default:
        return <CatalogPage />;
    }
  };

  return (
    <div className="app-layout">
      <Navbar />
      {renderCurrentView()}
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
