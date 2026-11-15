import { useState } from 'react';
import { getErrorMessage } from '../api/client';
import { deliveryApi, orderApi, ownerApi } from '../api/services';
import { DELIVERY_NEXT, OWNER_NEXT } from '../utils/constants';
import { StarInput } from './Common';
import Modal from './Modal';

/** Shared async-action helper: tracks busy state and reports errors to the parent. */
function useAction(onUpdated, onError) {
  const [busy, setBusy] = useState(false);
  const run = async (fn) => {
    setBusy(true);
    try {
      const result = await fn();
      onUpdated?.(result);
      return true;
    } catch (err) {
      onError?.(getErrorMessage(err));
      return false;
    } finally {
      setBusy(false);
    }
  };
  return [busy, run];
}

// ------------------------------------------------------------------ customer
export function CustomerOrderActions({ order, onUpdated, onError }) {
  const [busy, run] = useAction(onUpdated, onError);
  const [modal, setModal] = useState(null); // 'review' | 'return'
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [reason, setReason] = useState('');

  const cancel = () => {
    if (window.confirm(`Cancel order #${order.id}? Your dummy payment will be refunded.`)) run(() => orderApi.cancel(order.id));
  };
  const submitReview = async () => {
    const ok = await run(async () => {
      await orderApi.review(order.id, { rating, comment });
      return orderApi.get(order.id);
    });
    if (ok) setModal(null);
  };
  const submitReturn = async () => {
    const ok = await run(() => orderApi.requestReturn(order.id, reason));
    if (ok) setModal(null);
  };

  return (
    <>
      {order.can_cancel && <button className="btn btn-danger btn-sm" disabled={busy} onClick={cancel}>Cancel order</button>}
      {order.can_review && <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => setModal('review')}>★ Rate & review</button>}
      {order.can_request_return && <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setModal('return')}>Request return</button>}

      {modal === 'review' && (
        <Modal
          title={`Review order #${order.id}`} onClose={() => setModal(null)}
          footer={<button className="btn btn-primary" disabled={busy} onClick={submitReview}>{busy ? 'Submitting…' : 'Submit review'}</button>}
        >
          <p className="muted">How was your food from {order.restaurant.name}?</p>
          <StarInput value={rating} onChange={setRating} />
          <label className="field">
            <span>Comment (optional)</span>
            <textarea rows={3} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Tell others what you liked…" />
          </label>
        </Modal>
      )}
      {modal === 'return' && (
        <Modal
          title={`Request return / refund – #${order.id}`} onClose={() => setModal(null)}
          footer={(
            <button className="btn btn-primary" disabled={busy || reason.trim().length < 10} onClick={submitReturn}>
              {busy ? 'Submitting…' : 'Submit request'}
            </button>
          )}
        >
          <p className="muted small">You can submit only one return request per order. The restaurant will approve or reject it.</p>
          <label className="field">
            <span>Reason (min. 10 characters)</span>
            <textarea rows={4} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="What went wrong with your order?" />
          </label>
        </Modal>
      )}
    </>
  );
}

// ------------------------------------------------------------------ restaurant owner
export function OwnerOrderActions({ order, partners = [], onUpdated, onError }) {
  const [busy, run] = useAction(onUpdated, onError);
  const [partnerId, setPartnerId] = useState('');
  const next = OWNER_NEXT[order.status];

  return (
    <>
      {next && (
        <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => run(() => ownerApi.updateStatus(order.id, next.status))}>
          {next.label}
        </button>
      )}
      {order.status === 'PLACED' && (
        <button
          className="btn btn-danger btn-sm" disabled={busy}
          onClick={() => window.confirm(`Reject order #${order.id}? The customer will be refunded.`)
            && run(() => ownerApi.updateStatus(order.id, 'CANCELLED', 'Rejected by restaurant'))}
        >Reject</button>
      )}
      {order.status === 'READY' && (
        <span className="assign">
          <select aria-label="Delivery partner" value={partnerId} onChange={(e) => setPartnerId(e.target.value)}>
            <option value="">Choose rider…</option>
            {partners.map((p) => (
              <option key={p.id} value={p.id}>{p.name} ({p.active_deliveries} active)</option>
            ))}
          </select>
          <button className="btn btn-primary btn-sm" disabled={busy || !partnerId} onClick={() => run(() => ownerApi.assign(order.id, Number(partnerId)))}>
            Assign
          </button>
        </span>
      )}
    </>
  );
}

// ------------------------------------------------------------------ delivery partner
export function DeliveryOrderActions({ order, onUpdated, onError }) {
  const [busy, run] = useAction(onUpdated, onError);
  const next = DELIVERY_NEXT[order.status];
  if (!next) return null;
  return (
    <button
      className="btn btn-primary btn-sm" disabled={busy}
      onClick={() => (next.status !== 'DELIVERED' || window.confirm(`Confirm order #${order.id} was delivered?`))
        && run(() => deliveryApi.updateStatus(order.id, next.status))}
    >
      {busy ? 'Updating…' : next.label}
    </button>
  );
}
