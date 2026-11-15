import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getErrorMessage } from '../api/client';
import { Alert } from '../components/Common';
import { useAuth } from '../context/AuthContext';
import { ROLE_HOME, ROLE_LABELS, ROLES } from '../utils/constants';

const INITIAL = {
  name: '', email: '', password: '', confirm: '', role: ROLES.CUSTOMER, phone: '', address: '',
  restaurant_name: '', restaurant_cuisine: '', restaurant_address: '',
};

function validate(f) {
  if (f.name.trim().length < 2) return 'Please enter your full name.';
  if (!/^\S+@\S+\.\S+$/.test(f.email)) return 'Please enter a valid email address.';
  if (f.password.length < 8 || !/\d/.test(f.password) || !/[a-z]/i.test(f.password)) return 'Password needs 8+ characters with letters and numbers.';
  if (f.password !== f.confirm) return 'Passwords do not match.';
  if (f.role === ROLES.OWNER && !f.restaurant_name.trim()) return 'Please enter your restaurant name.';
  return '';
}

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const msg = validate(form);
    if (msg) return setError(msg);
    setError('');
    setLoading(true);
    try {
      const { confirm, ...payload } = form;
      if (payload.role !== ROLES.OWNER) {
        delete payload.restaurant_name; delete payload.restaurant_cuisine; delete payload.restaurant_address;
      }
      Object.keys(payload).forEach((k) => payload[k] === '' && delete payload[k]);
      const user = await register(payload);
      navigate(ROLE_HOME[user.role], { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card wide" onSubmit={submit} noValidate>
        <h1>Create your account</h1>
        <Alert onClose={() => setError('')}>{error}</Alert>

        <fieldset className="role-picker">
          <legend>I am a…</legend>
          {Object.values(ROLES).map((r) => (
            <label key={r} className={form.role === r ? 'selected' : ''}>
              <input type="radio" name="role" value={r} checked={form.role === r} onChange={set('role')} />
              {ROLE_LABELS[r]}
            </label>
          ))}
        </fieldset>

        <div className="grid-2">
          <label className="field"><span>Full name *</span><input value={form.name} onChange={set('name')} autoComplete="name" /></label>
          <label className="field"><span>Email *</span><input type="email" value={form.email} onChange={set('email')} autoComplete="email" /></label>
          <label className="field"><span>Password *</span><input type="password" value={form.password} onChange={set('password')} autoComplete="new-password" /></label>
          <label className="field"><span>Confirm password *</span><input type="password" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" /></label>
          <label className="field"><span>Phone</span><input type="tel" value={form.phone} onChange={set('phone')} autoComplete="tel" /></label>
          {form.role === ROLES.CUSTOMER && (
            <label className="field"><span>Delivery address</span><input value={form.address} onChange={set('address')} placeholder="Hostel / room / building" /></label>
          )}
        </div>

        {form.role === ROLES.OWNER && (
          <div className="grid-2 owner-fields">
            <label className="field"><span>Restaurant name *</span><input value={form.restaurant_name} onChange={set('restaurant_name')} /></label>
            <label className="field"><span>Cuisine</span><input value={form.restaurant_cuisine} onChange={set('restaurant_cuisine')} placeholder="e.g. Fast Food" /></label>
            <label className="field full"><span>Restaurant address</span><input value={form.restaurant_address} onChange={set('restaurant_address')} /></label>
          </div>
        )}

        <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Creating account…' : 'Create account'}</button>
        <p className="center small">Already have an account? <Link to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
