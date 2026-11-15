import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getErrorMessage } from '../../api/client';
import { ownerApi } from '../../api/services';
import { Alert, EmptyState, Loader, StatCard, StatusBadge } from '../../components/Common';
import Pagination from '../../components/Pagination';
import { useApi } from '../../hooks/useApi';
import { formatCurrency, humanize, timeAgo } from '../../utils/format';

function Reminders({ onChange }) {
  const [page, setPage] = useState(1);
  const [msg, setMsg] = useState('');
  const { data, loading, error, reload } = useApi(() => ownerApi.reminders({ page, page_size: 5 }), [page]);

  const resolve = async (id) => {
    try { await ownerApi.resolveReminder(id); reload(); onChange(); } catch (e) { setMsg(getErrorMessage(e)); }
  };
  const scan = async () => {
    try {
      await ownerApi.scanReminders();
      setMsg('Scan started in the background – refreshing…');
      setTimeout(() => { reload(); onChange(); setMsg(''); }, 1500);
    } catch (e) { setMsg(getErrorMessage(e)); }
  };

  return (
    <section className="card">
      <div className="row-between">
        <h2>⏰ Reminders</h2>
        <button className="btn btn-ghost btn-sm" onClick={scan}>Scan now</button>
      </div>
      <p className="muted small">Orders stuck in Placed / Accepted for more than 15 minutes (checked automatically every minute).</p>
      <Alert type="info" onClose={() => setMsg('')}>{msg}</Alert>
      <Alert>{error}</Alert>
      {loading && !data ? <Loader /> : data?.items.length ? (
        <ul className="reminder-list">
          {data.items.map((r) => (
            <li key={r.id}>
              <div>
                <Link to={`/orders/${r.order_id}`}><strong>Order #{r.order_id}</strong></Link> <StatusBadge status={r.order_status} />
                <div className="small">{r.message}</div>
                <div className="muted small">{timeAgo(r.created_at)}</div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => resolve(r.id)}>Dismiss</button>
            </li>
          ))}
        </ul>
      ) : <p className="muted">No pending reminders 🎉</p>}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </section>
  );
}

function RestaurantSettings({ restaurant, onSaved }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const toggleOpen = async () => {
    setBusy(true);
    try { onSaved(await ownerApi.updateRestaurant({ is_open: !restaurant.is_open })); } catch (e) { setErr(getErrorMessage(e)); }
    setBusy(false);
  };
  return (
    <section className="card restaurant-settings">
      <div>
        <h2>{restaurant.name}</h2>
        <p className="muted small">{restaurant.cuisine} · {restaurant.address}</p>
      </div>
      <Alert onClose={() => setErr('')}>{err}</Alert>
      <label className="switch">
        <input type="checkbox" checked={restaurant.is_open} disabled={busy} onChange={toggleOpen} />
        <span>{restaurant.is_open ? 'Open for orders' : 'Closed'}</span>
      </label>
    </section>
  );
}

export default function OwnerDashboard() {
  const { data: restaurant, setData: setRestaurant, error: rErr } = useApi(() => ownerApi.restaurant(), []);
  const { data: stats, loading, error, reload } = useApi(() => ownerApi.stats(), []);
  const maxDay = Math.max(1, ...(stats?.last_7_days || []).map((d) => d.orders));

  return (
    <div className="container page">
      <h1>Restaurant dashboard</h1>
      <Alert>{rErr || error}</Alert>
      {restaurant && <RestaurantSettings restaurant={restaurant} onSaved={setRestaurant} />}

      {loading && !stats ? <Loader text="Loading statistics…" /> : stats && (
        <>
          <div className="stats-grid">
            <StatCard label="Orders today" value={stats.orders_today} hint={`${formatCurrency(stats.revenue_today)} revenue`} />
            <StatCard label="Active orders" value={stats.active_orders} accent="blue" hint={<Link to="/owner/orders">Manage →</Link>} />
            <StatCard label="Total revenue" value={formatCurrency(stats.total_revenue)} accent="green" hint={`Avg ${formatCurrency(stats.average_order_value)} / order`} />
            <StatCard label="Rating" value={stats.avg_rating ? `${stats.avg_rating} ★` : '—'} hint={`${stats.review_count} reviews`} />
            <StatCard label="Delivered" value={stats.delivered_orders} hint={`${stats.cancelled_orders} cancelled`} />
            <StatCard label="Menu" value={`${stats.available_menu_items}/${stats.menu_items}`} hint={<Link to="/owner/menu">available dishes →</Link>} />
            <StatCard label="Pending returns" value={stats.pending_returns} accent={stats.pending_returns ? 'red' : ''} hint={<Link to="/owner/returns">Review →</Link>} />
            <StatCard label="Refunded" value={formatCurrency(stats.refunded_amount)} />
          </div>

          <div className="detail-grid">
            <section className="card">
              <h2>Last 7 days</h2>
              <div className="bar-chart" role="img" aria-label="Orders per day for the last 7 days">
                {stats.last_7_days.map((d) => (
                  <div key={d.date} className="bar-col" title={`${d.date}: ${d.orders} orders, ${formatCurrency(d.revenue)}`}>
                    <span className="bar-value">{d.orders}</span>
                    <div className="bar" style={{ height: `${(d.orders / maxDay) * 100}%` }} />
                    <span className="bar-label">{new Date(d.date).toLocaleDateString('en-IN', { weekday: 'short' })}</span>
                  </div>
                ))}
              </div>
            </section>
            <section className="card">
              <h2>Top dishes</h2>
              {stats.top_items.length ? (
                <table className="table">
                  <thead><tr><th>Dish</th><th className="num">Qty</th><th className="num">Revenue</th></tr></thead>
                  <tbody>{stats.top_items.map((t) => <tr key={t.name}><td>{t.name}</td><td className="num">{t.quantity}</td><td className="num">{formatCurrency(t.revenue)}</td></tr>)}</tbody>
                </table>
              ) : <EmptyState title="No sales yet" />}
              <h3>Orders by status</h3>
              <div className="chips">
                {stats.orders_by_status.map((s) => <span key={s.status} className={`badge status-${s.status.toLowerCase()}`}>{humanize(s.status)}: {s.count}</span>)}
              </div>
            </section>
          </div>
        </>
      )}
      <Reminders onChange={reload} />
    </div>
  );
}
