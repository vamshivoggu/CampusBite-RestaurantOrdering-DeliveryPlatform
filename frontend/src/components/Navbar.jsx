import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { ROLE_LABELS, ROLES } from '../utils/constants';

const LINKS = {
  guest: [{ to: '/restaurants', label: 'Restaurants' }],
  [ROLES.CUSTOMER]: [
    { to: '/restaurants', label: 'Restaurants' },
    { to: '/customer/dashboard', label: 'My Orders' },
    { to: '/customer/insights', label: '✨ AI Insights' },
  ],
  [ROLES.OWNER]: [
    { to: '/owner/dashboard', label: 'Dashboard' },
    { to: '/owner/orders', label: 'Orders' },
    { to: '/owner/menu', label: 'Menu' },
    { to: '/owner/returns', label: 'Returns' },
  ],
  [ROLES.DELIVERY]: [{ to: '/delivery/dashboard', label: 'My Deliveries' }],
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const links = LINKS[user?.role] || LINKS.guest;
  const close = () => setOpen(false);

  return (
    <header className="navbar">
      <div className="container nav-inner">
        <Link to="/" className="brand" onClick={close}>🍔 Campus<span>Bite</span></Link>
        <button className="nav-toggle" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>☰</button>
        <nav className={`nav-links ${open ? 'open' : ''}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} onClick={close}>{l.label}</NavLink>
          ))}
          {(!user || user.role === ROLES.CUSTOMER) && (
            <NavLink to="/cart" onClick={close} className="cart-link">
              🛒 Cart {count > 0 && <span className="cart-count">{count}</span>}
            </NavLink>
          )}
          {user ? (
            <div className="nav-user">
              <span className="nav-user-name" title={user.email}>
                {user.name.split(' ')[0]} <small>{ROLE_LABELS[user.role]}</small>
              </span>
              <button className="btn btn-ghost btn-sm" onClick={() => { close(); logout(); navigate('/login'); }}>Logout</button>
            </div>
          ) : (
            <div className="nav-user">
              <NavLink to="/login" onClick={close}>Login</NavLink>
              <Link to="/register" className="btn btn-primary btn-sm" onClick={close}>Sign up</Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
