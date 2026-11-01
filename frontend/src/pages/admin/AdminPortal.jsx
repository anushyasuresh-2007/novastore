import React, { useState } from "react";
import { useAdminAuth } from "../../context/AdminAuthContext";
import AdminNavbar from "../../components/admin/AdminNavbar";
import AdminLoginPage from "./AdminLoginPage";
import AdminDashboardPage from "./AdminDashboardPage";
import AdminProductsPage from "./AdminProductsPage";
import AdminOrdersPage from "./AdminOrdersPage";

export default function AdminPortal() {
  const { isAuthenticated, loading, activeTab, setActiveTab } = useAdminAuth();
  const [targetOrderRef, setTargetOrderRef] = useState(null);

  if (loading) {
    return (
      <div className="admin-loading-screen">
        <div className="button-spinner"></div>
        <p>Verifying administrator session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AdminLoginPage />;
  }

  const handleViewOrder = (orderRef) => {
    setTargetOrderRef(orderRef);
    setActiveTab("orders");
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case "products":
        return <AdminProductsPage />;
      case "orders":
        return <AdminOrdersPage initialOrderRef={targetOrderRef} />;
      case "dashboard":
      default:
        return <AdminDashboardPage onViewOrder={handleViewOrder} />;
    }
  };

  return (
    <div className="admin-layout">
      <AdminNavbar />
      <main className="admin-main-content">
        {renderActiveTab()}
      </main>
    </div>
  );
}
