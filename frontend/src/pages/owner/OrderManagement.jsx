import { useState } from 'react';
import { ownerApi } from '../../api/services';
import { Alert, EmptyState, Loader } from '../../components/Common';
import { OwnerOrderActions } from '../../components/OrderActions';
import OrderCard from '../../components/OrderCard';
import OrderFilters from '../../components/OrderFilters';
import Pagination from '../../components/Pagination';
import { useApi } from '../../hooks/useApi';
import { ORDER_STATUSES } from '../../utils/constants';

const QUICK = [
  { label: 'Needs action', value: ['PLACED', 'ACCEPTED', 'PREPARING', 'READY'] },
  { label: 'Out for delivery', value: ['ASSIGNED', 'OUT_FOR_DELIVERY'] },
  { label: 'All orders', value: [] },
];

export default function OrderManagement() {
  const [quick, setQuick] = useState(0);
  const [filters, setFilters] = useState({ status: '', date_from: '', date_to: '' });
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState('');
  const statusParam = filters.status ? [filters.status] : QUICK[quick].value;

  const { data, setData, loading, error, reload } = useApi(
    () => ownerApi.orders({ status: statusParam, date_from: filters.date_from, date_to: filters.date_to, page, page_size: 10 }),
    [statusParam.join(','), filters.date_from, filters.date_to, page],
  );
  const { data: partners, reload: reloadPartners } = useApi(() => ownerApi.partners(), []);

  const onUpdated = (updated) => {
    setActionError('');
    setData((d) => ({ ...d, items: d.items.map((o) => (o.id === updated.id ? updated : o)) }));
    if (updated.status === 'ASSIGNED') reloadPartners();
  };

  return (
    <div className="container page">
      <div className="row-between wrap">
        <h1>Order management</h1>
        <button className="btn btn-ghost btn-sm" onClick={reload}>↻ Refresh</button>
      </div>
      <div className="tabs" role="tablist">
        {QUICK.map((q, i) => (
          <button key={q.label} role="tab" aria-selected={quick === i && !filters.status} className={quick === i && !filters.status ? 'active' : ''}
            onClick={() => { setQuick(i); setFilters({ ...filters, status: '' }); setPage(1); }}>{q.label}</button>
        ))}
      </div>
      <OrderFilters filters={filters} statuses={ORDER_STATUSES} onChange={(f) => { setFilters(f); setPage(1); }} />
      <Alert>{error}</Alert>
      <Alert onClose={() => setActionError('')}>{actionError}</Alert>

      {loading && !data ? <Loader text="Loading orders…" /> : data?.items.length ? (
        <div className="order-list">
          {data.items.map((o) => (
            <OrderCard key={o.id} order={o} perspective="owner">
              <OwnerOrderActions order={o} partners={partners || []} onUpdated={onUpdated} onError={setActionError} />
            </OrderCard>
          ))}
        </div>
      ) : <EmptyState icon="📭" title="No orders match these filters" />}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
