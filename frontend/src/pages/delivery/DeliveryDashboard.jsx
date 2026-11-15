import { useState } from 'react';
import { deliveryApi } from '../../api/services';
import { Alert, EmptyState, Loader, StatCard } from '../../components/Common';
import { DeliveryOrderActions } from '../../components/OrderActions';
import OrderCard from '../../components/OrderCard';
import OrderFilters from '../../components/OrderFilters';
import Pagination from '../../components/Pagination';
import { useApi } from '../../hooks/useApi';

const SCOPES = {
  active: { label: 'Active deliveries', statuses: ['ASSIGNED', 'OUT_FOR_DELIVERY'] },
  history: { label: 'Delivery history', statuses: ['DELIVERED', 'REFUNDED'] },
};

export default function DeliveryDashboard() {
  const [scope, setScope] = useState('active');
  const [filters, setFilters] = useState({ status: '', date_from: '', date_to: '' });
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState('');
  const { data, loading, error, reload } = useApi(
    () => deliveryApi.orders({ scope, status: filters.status ? [filters.status] : [], date_from: filters.date_from, date_to: filters.date_to, page, page_size: 8 }),
    [scope, filters.status, filters.date_from, filters.date_to, page],
  );
  const { data: stats, reload: reloadStats } = useApi(() => deliveryApi.stats(), []);

  const onUpdated = () => { setActionError(''); reload(); reloadStats(); };
  const switchScope = (s) => { setScope(s); setFilters({ status: '', date_from: '', date_to: '' }); setPage(1); };

  return (
    <div className="container page">
      <div className="row-between wrap">
        <h1>🛵 My deliveries</h1>
        <button className="btn btn-ghost btn-sm" onClick={() => { reload(); reloadStats(); }}>↻ Refresh</button>
      </div>
      {stats && (
        <div className="stats-grid">
          <StatCard label="Active" value={stats.active} accent="blue" />
          <StatCard label="Delivered today" value={stats.delivered_today} accent="green" />
          <StatCard label="Total delivered" value={stats.delivered} />
        </div>
      )}
      <div className="tabs" role="tablist">
        {Object.entries(SCOPES).map(([k, v]) => (
          <button key={k} role="tab" aria-selected={scope === k} className={scope === k ? 'active' : ''} onClick={() => switchScope(k)}>{v.label}</button>
        ))}
      </div>
      <OrderFilters filters={filters} statuses={SCOPES[scope].statuses} showDates={scope === 'history'} onChange={(f) => { setFilters(f); setPage(1); }} />
      <Alert>{error}</Alert>
      <Alert onClose={() => setActionError('')}>{actionError}</Alert>

      {loading && !data ? <Loader /> : data?.items.length ? (
        <div className="order-list">
          {data.items.map((o) => (
            <OrderCard key={o.id} order={o} perspective="delivery">
              <DeliveryOrderActions order={o} onUpdated={onUpdated} onError={setActionError} />
            </OrderCard>
          ))}
        </div>
      ) : (
        <EmptyState icon="🛵" title={scope === 'active' ? 'No active deliveries' : 'No deliveries yet'}>
          {scope === 'active' && 'New orders appear here when a restaurant assigns them to you.'}
        </EmptyState>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
