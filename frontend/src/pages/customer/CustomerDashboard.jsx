import { useState } from 'react';
import { Link } from 'react-router-dom';
import { aiApi, orderApi } from '../../api/services';
import { Alert, EmptyState, Loader, StatCard } from '../../components/Common';
import { CustomerOrderActions } from '../../components/OrderActions';
import OrderCard from '../../components/OrderCard';
import OrderFilters from '../../components/OrderFilters';
import Pagination from '../../components/Pagination';
import { useAuth } from '../../context/AuthContext';
import { useApi } from '../../hooks/useApi';
import { ORDER_STATUSES } from '../../utils/constants';
import { formatCurrency } from '../../utils/format';

export default function CustomerDashboard() {
  const { user } = useAuth();
  const [filters, setFilters] = useState({ status: '', date_from: '', date_to: '' });
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState('');
  const { data, setData, loading, error } = useApi(
    () => orderApi.mine({ ...filters, page, page_size: 8 }),
    [filters.status, filters.date_from, filters.date_to, page],
  );
  const { data: stats, reload: reloadStats } = useApi(() => aiApi.stats(), []);

  const onUpdated = (updated) => {
    setActionError('');
    setData((d) => ({ ...d, items: d.items.map((o) => (o.id === updated.id ? updated : o)) }));
    reloadStats();
  };

  return (
    <div className="container page">
      <div className="row-between wrap">
        <h1>Hi {user.name.split(' ')[0]}, your orders</h1>
        <Link to="/customer/insights" className="btn btn-primary">✨ AI order insights</Link>
      </div>

      {stats && (
        <div className="stats-grid">
          <StatCard label="Total orders" value={stats.total_orders} />
          <StatCard label="In progress" value={stats.not_delivered_order_ids.length} accent="blue" />
          <StatCard label="Spent this week" value={formatCurrency(stats.spent_this_week)} accent="green" />
          <StatCard label="Total spent" value={formatCurrency(stats.total_spent)} hint={stats.refunded_total ? `${formatCurrency(stats.refunded_total)} refunded` : ''} />
        </div>
      )}

      <OrderFilters filters={filters} statuses={ORDER_STATUSES} onChange={(f) => { setFilters(f); setPage(1); }} />
      <Alert>{error}</Alert>
      <Alert onClose={() => setActionError('')}>{actionError}</Alert>

      {loading && !data ? <Loader text="Loading your orders…" /> : data?.items.length ? (
        <div className="order-list">
          {data.items.map((o) => (
            <OrderCard key={o.id} order={o}>
              <CustomerOrderActions order={o} onUpdated={onUpdated} onError={setActionError} />
            </OrderCard>
          ))}
        </div>
      ) : (
        <EmptyState icon="🧾" title="No orders found">
          {filters.status || filters.date_from || filters.date_to ? 'Try clearing the filters.' : <Link to="/restaurants" className="btn btn-primary">Order something tasty</Link>}
        </EmptyState>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
