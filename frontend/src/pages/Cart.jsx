import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getErrorMessage } from '../api/client';
import { metaApi, orderApi } from '../api/services';
import { Alert, EmptyState, VegMark } from '../components/Common';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useApi } from '../hooks/useApi';
import { PAYMENT_METHODS } from '../utils/constants';
import { formatCurrency } from '../utils/format';

export default function Cart() {
  const { user } = useAuth();
  const { cart, subtotal, updateQuantity, removeItem, clearCart } = useCart();
  const navigate = useNavigate();
  const { data: meta } = useApi(() => metaApi.get(), []);
  const [address, setAddress] = useState(user?.address || '');
  const [notes, setNotes] = useState('');
  const [method, setMethod] = useState('mock_card');
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState('');

  const fee = meta?.delivery_fee ?? 30;
  const total = subtotal + fee;

  if (!cart.items.length) {
    return (
      <div className="container page narrow">
        <EmptyState icon="🛒" title="Your cart is empty">
          <Link to="/restaurants" className="btn btn-primary">Browse restaurants</Link>
        </EmptyState>
      </div>
    );
  }

  const placeOrder = async (e) => {
    e.preventDefault();
    if (address.trim().length < 5) return setError('Please enter a complete delivery address.');
    setError('');
    setPlacing(true);
    try {
      const order = await orderApi.place({
        restaurant_id: cart.restaurantId,
        items: cart.items.map((i) => ({ menu_item_id: i.id, quantity: i.quantity })),
        delivery_address: address.trim(),
        notes: notes.trim() || null,
        payment_method: method,
      });
      clearCart();
      navigate(`/orders/${order.id}`, { state: { justPlaced: true } });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setPlacing(false);
    }
  };

  return (
    <div className="container page">
      <h1>Your cart</h1>
      <div className="checkout-layout">
        <section className="card">
          <div className="row-between">
            <h2>{cart.restaurantName}</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => window.confirm('Remove all items?') && clearCart()}>Clear cart</button>
          </div>
          <ul className="cart-list">
            {cart.items.map((i) => (
              <li key={i.id}>
                <div className="grow"><VegMark veg={i.is_veg} /> {i.name}<div className="muted small">{formatCurrency(i.price)} each</div></div>
                <div className="qty">
                  <button onClick={() => updateQuantity(i.id, i.quantity - 1)} aria-label={`Decrease ${i.name}`}>−</button>
                  <span>{i.quantity}</span>
                  <button onClick={() => updateQuantity(i.id, i.quantity + 1)} aria-label={`Increase ${i.name}`}>+</button>
                </div>
                <strong className="line-total">{formatCurrency(i.price * i.quantity)}</strong>
                <button className="icon-btn" onClick={() => removeItem(i.id)} aria-label={`Remove ${i.name}`}>🗑</button>
              </li>
            ))}
          </ul>
          <Link to={`/restaurants/${cart.restaurantId}`} className="small">+ Add more items</Link>
        </section>

        <form className="card checkout" onSubmit={placeOrder}>
          <h2>Checkout</h2>
          {!user ? (
            <>
              <p className="muted">Please log in as a customer to place your order.</p>
              <Link to="/login" state={{ from: '/cart' }} className="btn btn-primary btn-block">Log in to checkout</Link>
            </>
          ) : user.role !== 'customer' ? (
            <Alert type="info">Only customer accounts can place orders.</Alert>
          ) : (
            <>
              <Alert onClose={() => setError('')}>{error}</Alert>
              <label className="field"><span>Delivery address *</span>
                <textarea rows={2} value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Hostel, room no., landmark" required />
              </label>
              <label className="field"><span>Notes for the restaurant</span>
                <input value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} placeholder="Less spicy, no onions…" />
              </label>
              <fieldset className="pay-methods">
                <legend>Payment method</legend>
                {PAYMENT_METHODS.map((m) => (
                  <label key={m.value} className={method === m.value ? 'selected' : ''}>
                    <input type="radio" name="pay" value={m.value} checked={method === m.value} onChange={(e) => setMethod(e.target.value)} />
                    {m.label}
                  </label>
                ))}
              </fieldset>
              <p className="muted small">🔒 This is a dummy payment – no real money is charged.</p>
              <dl className="totals">
                <dt>Subtotal</dt><dd>{formatCurrency(subtotal)}</dd>
                <dt>Delivery fee</dt><dd>{formatCurrency(fee)}</dd>
                <dt className="total">Total</dt><dd className="total">{formatCurrency(total)}</dd>
              </dl>
              <button className="btn btn-primary btn-block" disabled={placing}>
                {placing ? 'Processing payment…' : `Pay ${formatCurrency(total)} & place order`}
              </button>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
