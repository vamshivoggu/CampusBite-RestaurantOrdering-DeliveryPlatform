import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getErrorMessage } from '../api/client';
import { Alert } from '../components/Common';
import { useAuth } from '../context/AuthContext';
import { ROLE_HOME } from '../utils/constants';

const DEMO = [
  { label: 'Customer', email: 'customer@campusbite.dev' },
  { label: 'Owner', email: 'owner@campusbite.dev' },
  { label: 'Rider', email: 'rider@campusbite.dev' },
];

export default function Login() {
  const { login, sessionMessage, setSessionMessage } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(form.email, form.password);
      const from = location.state?.from;
      // only honour the redirect for customers (e.g. returning to /cart)
      navigate(from && user.role === 'customer' ? from : ROLE_HOME[user.role], { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit} noValidate>
        <h1>Welcome back 👋</h1>
        <p className="muted">Log in to order, manage your restaurant or your deliveries.</p>
        <Alert type="info" onClose={() => setSessionMessage('')}>{sessionMessage}</Alert>
        <Alert onClose={() => setError('')}>{error}</Alert>
        <label className="field">
          <span>Email</span>
          <input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label className="field">
          <span>Password</span>
          <input type="password" autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>
        <button className="btn btn-primary btn-block" disabled={loading || !form.email || !form.password}>
          {loading ? 'Logging in…' : 'Log in'}
        </button>
        <p className="center small">New here? <Link to="/register">Create an account</Link></p>
        <div className="demo-box">
          <span className="small muted">Demo accounts (password <code>Password@123</code>):</span>
          <div className="demo-buttons">
            {DEMO.map((d) => (
              <button type="button" key={d.email} className="btn btn-ghost btn-sm" onClick={() => setForm({ email: d.email, password: 'Password@123' })}>
                {d.label}
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
}
