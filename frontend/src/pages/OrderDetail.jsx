import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { orderApi, ownerApi } from '../api/services';
import { Alert, Loader, PaymentBadge, ReturnBadge, Stars, StatusBadge } from '../components/Common';
import { CustomerOrderActions, DeliveryOrderActions, OwnerOrderActions } from '../components/OrderActions';
import OrderTracker from '../components/OrderTracker';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../hooks/useApi';
import { ROLE_HOME } from '../utils/constants';
import { formatCurrency, formatDateTime, humanize } from '../utils/format';

const ACTIVE = ['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY'];

export default function OrderDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const location = useLocation();
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState(location.state?.justPlaced ? '🎉 Order placed and paid (dummy payment). Track its progress below.' : '');
  const { data: order, setData, loading, error, reload } = useApi(() => orderApi.get(id), [id]);
  const isOwner = user.role === 'restaurant_owner';
  const { data: partners } = useApi(() => (isOwner && order?.status === 'READY' ? ownerApi.partners() : Promise.resolve([])), [isOwner, order?.status]);

  // Light polling so customers see status changes without refreshing (no WebSockets needed).
  useEffect(() => {
    if (!order || !ACTIVE.includes(order.status)) return undefined;
    const t = setInterval(() => orderApi.get(id).then(setData).catch(() => {}), 20000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, order?.status, setData]);

  if (loading && !order) return <div className="container page"><Loader /></div>;
  if (error) return <div className="container page"><Alert>{error}</Alert><Link to={ROLE_HOME[user.role]}>← Back</Link></div>;
  if (!order) return null;

  const onUpdated = (o) => { setActionError(''); if (o?.id) setData(o); else reload(); };
  const actionProps = { order, onUpdated, onError: setActionError };

  return (
    <div className="container page">
      <Link to={ROLE_HOME[user.role] === '/restaurants' ? '/customer/dashboard' : ROLE_HOME[user.role]} className="back-link">← Back to dashboard</Link>
      <Alert type="success" onClose={() => setNotice('')}>{notice}</Alert>
      <Alert onClose={() => setActionError('')}>{actionError}</Alert>

      <div className="row-between wrap">
        <h1>Order #{order.id}</h1>
        <div className="badges"><StatusBadge status={order.status} /><PaymentBadge status={order.payment_status} /><ReturnBadge status={order.return_status} /></div>
      </div>
      <p className="muted">Placed {formatDateTime(order.created_at)} · {order.restaurant.name}</p>

      <section className="card"><OrderTracker status={order.status} /></section>

      <div className="actions-bar">
        {user.role === 'customer' && <CustomerOrderActions {...actionProps} />}
        {isOwner && <OwnerOrderActions {...actionProps} partners={partners || []} />}
        {user.role === 'delivery_partner' && <DeliveryOrderActions {...actionProps} />}
      </div>

      <div className="detail-grid">
        <section className="card">
          <h2>Items</h2>
          <table className="table">
            <thead><tr><th>Dish</th><th>Qty</th><th className="num">Price</th><th className="num">Total</th></tr></thead>
            <tbody>
              {order.items.map((i) => (
                <tr key={i.id}><td>{i.name}</td><td>{i.quantity}</td><td className="num">{formatCurrency(i.unit_price)}</td><td className="num">{formatCurrency(i.subtotal)}</td></tr>
              ))}
            </tbody>
          </table>
          <dl className="totals">
            <dt>Subtotal</dt><dd>{formatCurrency(order.subtotal)}</dd>
            <dt>Delivery fee</dt><dd>{formatCurrency(order.delivery_fee)}</dd>
            <dt className="total">Total</dt><dd className="total">{formatCurrency(order.total_amount)}</dd>
          </dl>
          {order.notes && <p className="small">📝 {order.notes}</p>}
        </section>

        <section className="card">
          <h2>Delivery</h2>
          <p><span className="muted">Customer:</span> {order.customer.name} {order.customer.phone && <a href={`tel:${order.customer.phone}`}>({order.customer.phone})</a>}</p>
          <p><span className="muted">Address:</span> {order.delivery_address}</p>
          <p><span className="muted">Restaurant:</span> {order.restaurant.name}{order.restaurant.address ? `, ${order.restaurant.address}` : ''}</p>
          <p><span className="muted">Delivery partner:</span> {order.delivery_partner ? `${order.delivery_partner.name}${order.delivery_partner.phone ? ` (${order.delivery_partner.phone})` : ''}` : 'Not assigned yet'}</p>
          {order.delivered_at && <p><span className="muted">Delivered:</span> {formatDateTime(order.delivered_at)}</p>}
        </section>

        <section className="card">
          <h2>Payment</h2>
          <p><span className="muted">Method:</span> {humanize(order.payment_method.replace('mock_', ''))} (dummy)</p>
          <ul className="ledger">
            {order.ledger_entries.map((e) => (
              <li key={e.id}>
                <span className={`badge ${e.entry_type === 'refund' ? 'pay-refunded' : 'pay-mock_paid'}`}>{e.entry_type}</span>
                <strong>{e.entry_type === 'refund' ? '−' : ''}{formatCurrency(e.amount)}</strong>
                <span className="muted small">{e.reference} · {formatDateTime(e.created_at)}</span>
              </li>
            ))}
          </ul>
          {order.return_status !== 'none' && (
            <div className="return-box">
              <h3>Return / refund <ReturnBadge status={order.return_status} /></h3>
              <p className="small">“{order.return_reason}”</p>
              {order.return_resolution_note && <p className="small"><span className="muted">Restaurant note:</span> {order.return_resolution_note}</p>}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Timeline</h2>
          <ol className="timeline">
            {order.history.map((h) => (
              <li key={h.id}>
                <StatusBadge status={h.to_status} />
                <span className="small">{formatDateTime(h.created_at)}{h.changed_by_role ? ` · by ${humanize(h.changed_by_role)}` : ''}</span>
                {h.note && <span className="muted small"> — {h.note}</span>}
              </li>
            ))}
          </ol>
          {order.review && (
            <div className="return-box">
              <h3>Your review</h3>
              <Stars value={order.review.rating} />
              {order.review.comment && <p className="small">{order.review.comment}</p>}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
