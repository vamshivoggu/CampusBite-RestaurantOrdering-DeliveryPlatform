import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const CART_KEY = 'campusbite_cart';
const EMPTY = { restaurantId: null, restaurantName: '', items: [] };
const CartContext = createContext(null);

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || EMPTY;
  } catch {
    return EMPTY;
  }
}

/** Cart lives in React state (persisted to localStorage). A cart holds dishes from one restaurant. */
export function CartProvider({ children }) {
  const [cart, setCart] = useState(readCart);

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  }, [cart]);

  /** Returns false if the dish is from another restaurant and the user declined to replace the cart. */
  const addItem = (dish, restaurant) => {
    if (cart.restaurantId && cart.restaurantId !== restaurant.id && cart.items.length) {
      const ok = window.confirm(
        `Your cart has dishes from ${cart.restaurantName}. Start a new cart with ${restaurant.name}?`,
      );
      if (!ok) return false;
      setCart({ restaurantId: restaurant.id, restaurantName: restaurant.name, items: [{ ...pick(dish), quantity: 1 }] });
      return true;
    }
    setCart((c) => {
      const existing = c.items.find((i) => i.id === dish.id);
      const items = existing
        ? c.items.map((i) => (i.id === dish.id ? { ...i, quantity: Math.min(i.quantity + 1, 50) } : i))
        : [...c.items, { ...pick(dish), quantity: 1 }];
      return { restaurantId: restaurant.id, restaurantName: restaurant.name, items };
    });
    return true;
  };

  const updateQuantity = (id, quantity) => {
    setCart((c) => {
      const items = quantity <= 0
        ? c.items.filter((i) => i.id !== id)
        : c.items.map((i) => (i.id === id ? { ...i, quantity: Math.min(quantity, 50) } : i));
      return items.length ? { ...c, items } : EMPTY;
    });
  };

  const removeItem = (id) => updateQuantity(id, 0);
  const clearCart = () => setCart(EMPTY);

  const value = useMemo(() => {
    const count = cart.items.reduce((n, i) => n + i.quantity, 0);
    const subtotal = cart.items.reduce((s, i) => s + i.price * i.quantity, 0);
    const quantityOf = (id) => cart.items.find((i) => i.id === id)?.quantity || 0;
    return { cart, count, subtotal, quantityOf, addItem, updateQuantity, removeItem, clearCart };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

const pick = (d) => ({ id: d.id, name: d.name, price: d.price, is_veg: d.is_veg });

export const useCart = () => useContext(CartContext);
