import React, { createContext, useContext, useState, useEffect } from "react";
import {
  adminLogin as apiLogin,
  adminLogout as apiLogout,
  fetchAdminMe,
  getAdminToken,
} from "../services/adminApi";

const AdminAuthContext = createContext();

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [token, setToken] = useState(() => getAdminToken());
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard"); // "dashboard" | "products" | "orders"

  // Verify session on mount if token is present
  useEffect(() => {
    let isMounted = true;
    async function verifySession() {
      const storedToken = getAdminToken();
      if (!storedToken) {
        if (isMounted) setLoading(false);
        return;
      }

      try {
        const data = await fetchAdminMe();
        if (isMounted && data.admin) {
          setAdmin(data.admin);
          setToken(storedToken);
        }
      } catch (err) {
        console.warn("Stored admin token was invalid or expired:", err);
        if (isMounted) {
          setAdmin(null);
          setToken(null);
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

  const login = async (username, password) => {
    const data = await apiLogin(username, password);
    setAdmin(data.admin);
    setToken(data.token);
    return data;
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch (err) {
      console.warn("Logout request failed:", err);
    } finally {
      setAdmin(null);
      setToken(null);
      setActiveTab("dashboard");
    }
  };

  const isAuthenticated = Boolean(admin && token);

  return (
    <AdminAuthContext.Provider
      value={{
        admin,
        token,
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
