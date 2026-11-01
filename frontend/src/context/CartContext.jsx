import React, { createContext, useContext, useState, useEffect } from "react";

const CartContext = createContext();

const LOCAL_STORAGE_KEY = "novastore_cart_items";

export function CartProvider({ children }) {
  const [cartItems, setCartItems] = useState(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (err) {
      console.error("Error reading cart from localStorage:", err);
      return [];
    }
  });

  const [notification, setNotification] = useState(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [currentView, setCurrentView] = useState("catalog"); // "catalog" | "cart" | "checkout" | "confirmation"
  const [confirmedOrder, setConfirmedOrder] = useState(null);

  // Persist to localStorage whenever cartItems changes
  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(cartItems));
    } catch (err) {
      console.error("Error saving cart to localStorage:", err);
    }
  }, [cartItems]);

  const showNotification = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 3500);
  };

  /**
   * Add a product to the cart with strict stock availability checking.
   * @param {Object} product
   * @param {number} quantityToAdd
   * @returns {{ success: boolean, message: string }}
   */
  const addToCart = (product, quantityToAdd = 1) => {
    if (!product || product.stock_quantity <= 0) {
      const msg = `"${product?.name || "Product"}" is currently out of stock.`;
      showNotification(msg, "error");
      return { success: false, message: msg };
    }

    const qtyToAdd = Math.max(1, parseInt(quantityToAdd, 10) || 1);
    const existingIndex = cartItems.findIndex((item) => item.id === product.id);

    if (existingIndex > -1) {
      const currentQty = cartItems[existingIndex].quantity;
      const newTotalQty = currentQty + qtyToAdd;

      if (newTotalQty > product.stock_quantity) {
        const allowedToAdd = product.stock_quantity - currentQty;
        if (allowedToAdd <= 0) {
          const msg = `You already have all ${product.stock_quantity} available units of "${product.name}" in your cart.`;
          showNotification(msg, "warning");
          return { success: false, message: msg };
        } else {
          // Add remaining allowed stock
          const updatedItems = [...cartItems];
          updatedItems[existingIndex].quantity = product.stock_quantity;
          setCartItems(updatedItems);
          const msg = `Added ${allowedToAdd} remaining unit(s). Cart reached maximum available stock (${product.stock_quantity}).`;
          showNotification(msg, "warning");
          return { success: true, message: msg };
        }
      } else {
        const updatedItems = [...cartItems];
        updatedItems[existingIndex].quantity = newTotalQty;
        setCartItems(updatedItems);
        const msg = `Updated "${product.name}" quantity to ${newTotalQty}.`;
        showNotification(msg, "success");
        return { success: true, message: msg };
      }
    } else {
      if (qtyToAdd > product.stock_quantity) {
        const msg = `Cannot add ${qtyToAdd} units. Only ${product.stock_quantity} units available.`;
        showNotification(msg, "error");
        return { success: false, message: msg };
      }

      const newItem = {
        id: product.id,
        name: product.name,
        price: Number(product.price),
        stock_quantity: Number(product.stock_quantity),
        image_path: product.image_path,
        category: product.category,
        quantity: qtyToAdd,
      };

      setCartItems((prev) => [...prev, newItem]);
      const msg = `Added "${product.name}" to your cart.`;
      showNotification(msg, "success");
      return { success: true, message: msg };
    }
  };

  /**
   * Update quantity of an existing item.
   * @param {number} productId
   * @param {number} newQuantity
   */
  const updateQuantity = (productId, newQuantity) => {
    const qty = parseInt(newQuantity, 10);
    if (isNaN(qty) || qty < 1) return;

    setCartItems((prevItems) =>
      prevItems.map((item) => {
        if (item.id !== productId) return item;

        if (qty > item.stock_quantity) {
          showNotification(
            `Cannot exceed maximum available stock of ${item.stock_quantity} for "${item.name}".`,
            "warning"
          );
          return { ...item, quantity: item.stock_quantity };
        }

        return { ...item, quantity: qty };
      })
    );
  };

  /**
   * Remove a single item from the cart.
   * @param {number} productId
   */
  const removeFromCart = (productId) => {
    setCartItems((prev) => {
      const removed = prev.find((item) => item.id === productId);
      if (removed) {
        showNotification(`Removed "${removed.name}" from your cart.`, "info");
      }
      return prev.filter((item) => item.id !== productId);
    });
  };

  /**
   * Empty the entire cart.
   */
  const clearCart = () => {
    if (cartItems.length > 0) {
      setCartItems([]);
      showNotification("Shopping cart cleared.", "info");
    }
  };

  /**
   * Total quantity of all items in cart.
   */
  const totalItemCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);

  /**
   * Subtotal calculated from item prices and quantities.
   */
  const subtotal = cartItems.reduce(
    (acc, item) => acc + Number(item.price) * item.quantity,
    0
  );

  /**
   * Delivery fee logic: Free if subtotal >= 100, otherwise $5.00 flat fee (or $0 if cart empty).
   */
  const deliveryFee = cartItems.length === 0 ? 0 : subtotal >= 100 ? 0 : 5.0;

  /**
   * Final total amount estimate.
   */
  const totalAmount = subtotal + deliveryFee;

  return (
    <CartContext.Provider
      value={{
        cartItems,
        totalItemCount,
        subtotal,
        deliveryFee,
        totalAmount,
        notification,
        isCartOpen,
        currentView,
        setCurrentView,
        confirmedOrder,
        setConfirmedOrder,
        setIsCartOpen,
        goToCatalog: () => setCurrentView("catalog"),
        goToCart: () => setCurrentView("cart"),
        goToCheckout: () => setCurrentView("checkout"),
        goToConfirmation: (order) => {
          setConfirmedOrder(order);
          setCurrentView("confirmation");
        },
        openCart: () => {
          setIsCartOpen(true);
          setCurrentView("cart");
        },
        closeCart: () => {
          setIsCartOpen(false);
          setCurrentView("catalog");
        },
        toggleCart: () => {
          setCurrentView((prev) => (prev === "cart" ? "catalog" : "cart"));
        },
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        showNotification,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
