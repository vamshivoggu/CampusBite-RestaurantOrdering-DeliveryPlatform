import { LIFECYCLE } from '../utils/constants';
import { humanize } from '../utils/format';

/** Visual progress bar for the order lifecycle. */
export default function OrderTracker({ status }) {
  if (status === 'CANCELLED' || status === 'REFUNDED') {
    return (
      <div className={`tracker-terminal status-${status.toLowerCase()}`}>
        {status === 'CANCELLED' ? '✕ This order was cancelled' : '↩ This order was returned and refunded'}
      </div>
    );
  }
  const current = LIFECYCLE.indexOf(status);
  return (
    <ol className="tracker" aria-label="Order progress">
      {LIFECYCLE.map((s, i) => (
        <li key={s} className={i < current ? 'done' : i === current ? 'current' : ''} aria-current={i === current ? 'step' : undefined}>
          <span className="dot">{i < current ? '✓' : i + 1}</span>
          <span className="label">{humanize(s)}</span>
        </li>
      ))}
    </ol>
  );
}
