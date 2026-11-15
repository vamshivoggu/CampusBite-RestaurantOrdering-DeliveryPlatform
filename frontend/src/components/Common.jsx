/** Small, reusable presentational components. */
import { humanize } from '../utils/format';

export function Loader({ text = 'Loading…' }) {
  return (
    <div className="loader" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

export function Alert({ type = 'error', children, onClose }) {
  if (!children) return null;
  return (
    <div className={`alert alert-${type}`} role={type === 'error' ? 'alert' : 'status'}>
      <span>{children}</span>
      {onClose && (
        <button className="alert-close" onClick={onClose} aria-label="Dismiss">×</button>
      )}
    </div>
  );
}

export function EmptyState({ icon = '🍽️', title, children }) {
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden="true">{icon}</div>
      <h3>{title}</h3>
      {children && <div className="muted">{children}</div>}
    </div>
  );
}

export function StatusBadge({ status }) {
  return <span className={`badge status-${(status || '').toLowerCase()}`}>{humanize(status)}</span>;
}

export function PaymentBadge({ status }) {
  const label = { mock_paid: 'Paid (dummy)', refunded: 'Refunded', pending: 'Pending', failed: 'Failed' }[status] || status;
  return <span className={`badge pay-${status}`}>{label}</span>;
}

export function ReturnBadge({ status }) {
  if (!status || status === 'none') return null;
  return <span className={`badge return-${status}`}>Return {status}</span>;
}

export function VegMark({ veg }) {
  return <span className={`veg-mark ${veg ? 'veg' : 'nonveg'}`} title={veg ? 'Vegetarian' : 'Non-vegetarian'} />;
}

export function StatCard({ label, value, hint, accent }) {
  return (
    <div className={`stat-card ${accent ? `accent-${accent}` : ''}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

export function Stars({ value = 0, size = 'sm' }) {
  const rounded = Math.round(value);
  return (
    <span className={`stars stars-${size}`} aria-label={`${value} out of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= rounded ? 'on' : ''}>★</span>
      ))}
    </span>
  );
}

export function StarInput({ value, onChange }) {
  return (
    <div className="star-input" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          type="button" key={i} role="radio" aria-checked={value === i} aria-label={`${i} star${i > 1 ? 's' : ''}`}
          className={i <= value ? 'on' : ''} onClick={() => onChange(i)}
        >★</button>
      ))}
    </div>
  );
}
