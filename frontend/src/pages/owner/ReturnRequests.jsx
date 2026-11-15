import { useState } from 'react';
import { getErrorMessage } from '../../api/client';
import { ownerApi } from '../../api/services';
import { Alert, EmptyState, Loader } from '../../components/Common';
import Modal from '../../components/Modal';
import OrderCard from '../../components/OrderCard';
import Pagination from '../../components/Pagination';
import { useApi } from '../../hooks/useApi';
import { formatCurrency } from '../../utils/format';

const TABS = [
  { label: 'Pending', value: 'requested' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'All', value: '' },
];

export default function ReturnRequests() {
  const [tab, setTab] = useState('requested');
  const [page, setPage] = useState(1);
  const [decision, setDecision] = useState(null); // { order, type }
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { data, loading, error: loadError, reload } = useApi(
    () => ownerApi.returns({ return_status: tab, page, page_size: 8 }),
    [tab, page],
  );

  const submit = async () => {
    setBusy(true);
    try {
      const o = await ownerApi.decideReturn(decision.order.id, decision.type, note.trim() || null);
      setNotice(decision.type === 'approve'
        ? `Return approved – ${formatCurrency(o.total_amount)} refunded for order #${o.id}.`
        : `Return for order #${o.id} rejected.`);
      setDecision(null);
      setNote('');
      reload();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container page">
      <h1>Return & refund requests</h1>
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.label} role="tab" aria-selected={tab === t.value} className={tab === t.value ? 'active' : ''} onClick={() => { setTab(t.value); setPage(1); }}>{t.label}</button>
        ))}
      </div>
      <Alert type="success" onClose={() => setNotice('')}>{notice}</Alert>
      <Alert onClose={() => setError('')}>{error || loadError}</Alert>

      {loading && !data ? <Loader /> : data?.items.length ? (
        <div className="order-list">
          {data.items.map((o) => (
            <OrderCard key={o.id} order={o} perspective="owner">
              {o.return_status === 'requested' && (
                <>
                  <button className="btn btn-primary btn-sm" onClick={() => setDecision({ order: o, type: 'approve' })}>Approve refund</button>
                  <button className="btn btn-danger btn-sm" onClick={() => setDecision({ order: o, type: 'reject' })}>Reject</button>
                </>
              )}
              {o.return_resolution_note && <span className="muted small">Note: {o.return_resolution_note}</span>}
            </OrderCard>
          ))}
        </div>
      ) : <EmptyState icon="↩️" title="No return requests here" />}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}

      {decision && (
        <Modal
          title={`${decision.type === 'approve' ? 'Approve' : 'Reject'} return – order #${decision.order.id}`}
          onClose={() => setDecision(null)}
          footer={(
            <button className={`btn ${decision.type === 'approve' ? 'btn-primary' : 'btn-danger'}`} disabled={busy} onClick={submit}>
              {busy ? 'Saving…' : decision.type === 'approve' ? `Refund ${formatCurrency(decision.order.total_amount)}` : 'Reject request'}
            </button>
          )}
        >
          <p className="small"><span className="muted">Customer reason:</span> “{decision.order.return_reason}”</p>
          <label className="field"><span>Note to customer (optional)</span>
            <textarea rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
        </Modal>
      )}
    </div>
  );
}
