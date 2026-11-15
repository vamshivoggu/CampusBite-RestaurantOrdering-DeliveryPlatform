import { Link } from 'react-router-dom';
import { formatCurrency, formatDateTime, timeAgo } from '../utils/format';
import { PaymentBadge, ReturnBadge, StatusBadge } from './Common';

/**
 * Compact order summary used on every dashboard.
 * `perspective` controls which party is highlighted; `children` renders role-specific actions.
 */
export default function OrderCard({ order, perspective = 'customer', children }) {
  const itemsText = order.items.map((i) => `${i.quantity}× ${i.name}`).join(', ');
  return (
    <article className="card order-card">
      <div className="order-card-head">
        <div>
          <Link to={`/orders/${order.id}`} className="order-id">Order #{order.id}</Link>
          <div className="muted small" title={formatDateTime(order.created_at)}>
            {formatDateTime(order.created_at)} · updated {timeAgo(order.status_updated_at)}
          </div>
        </div>
        <div className="badges">
          <StatusBadge status={order.status} />
          <PaymentBadge status={order.payment_status} />
          <ReturnBadge status={order.return_status} />
        </div>
      </div>

      <div className="order-card-body">
        {perspective === 'customer' && <p><strong>{order.restaurant.name}</strong></p>}
        {perspective !== 'customer' && (
          <p>
            <strong>{order.customer.name}</strong>
            {order.customer.phone && <> · <a href={`tel:${order.customer.phone}`}>{order.customer.phone}</a></>}
          </p>
        )}
        {perspective === 'delivery' && (
          <>
            <p className="small"><span className="muted">Pickup:</span> {order.restaurant.name}{order.restaurant.address ? `, ${order.restaurant.address}` : ''}</p>
            <p className="small"><span className="muted">Deliver to:</span> {order.delivery_address}</p>
          </>
        )}
        <p className="small muted order-items-text">{itemsText}</p>
        {order.notes && <p className="small">📝 {order.notes}</p>}
        {perspective === 'owner' && order.delivery_partner && (
          <p className="small">🛵 {order.delivery_partner.name}</p>
        )}
        {order.return_status === 'requested' && order.return_reason && (
          <p className="small return-reason">Return reason: “{order.return_reason}”</p>
        )}
      </div>

      <div className="order-card-foot">
        <strong>{formatCurrency(order.total_amount)}</strong>
        <div className="actions">
          {children}
          <Link to={`/orders/${order.id}`} className="btn btn-ghost btn-sm">Details</Link>
        </div>
      </div>
    </article>
  );
}
