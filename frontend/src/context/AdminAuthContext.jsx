import React, { createContext, useContext, useState, useEffect } from "react";
import {
  adminLogin as apiLogin,
  adminLogout as apiLogout,
  fetchAdminMe,
} from "../services/adminApi";

const AdminAuthContext = createContext();

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard"); // "dashboard" | "products" | "orders"

  // Verify session on mount via HttpOnly cookie
  useEffect(() => {
    let isMounted = true;
    async function verifySession() {
      try {
        const data = await fetchAdminMe();
        if (isMounted && data.admin) {
          setAdmin(data.admin);
        }
      } catch (err) {
        // No active session or expired cookie
        if (isMounted) {
          setAdmin(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    verifySession();
    return () => {
      isMounted = false;
    };
  }, []);

  // Listen for unauthorized/expired session events from API client
  useEffect(() => {
    const handleUnauthorized = () => {
      setAdmin(null);
    };

    if (typeof window !== "undefined") {
      window.addEventListener("admin:unauthorized", handleUnauthorized);
      return () => {
        window.removeEventListener("admin:unauthorized", handleUnauthorized);
      };
    }
  }, []);

  const login = async (username, password) => {
    const data = await apiLogin(username, password);
    setAdmin(data.admin);
    return data;
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch (err) {
      console.warn("Logout request failed:", err);
    } finally {
      setAdmin(null);
      setActiveTab("dashboard");
    }
  };

  const isAuthenticated = Boolean(admin);

  return (
    <AdminAuthContext.Provider
      value={{
        admin,
        token: null, // Legacy compatibility
        isAuthenticated,
        loading,
        activeTab,
        setActiveTab,
        login,
        logout,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error("useAdminAuth must be used within an AdminAuthProvider");
  }
  return context;
}
