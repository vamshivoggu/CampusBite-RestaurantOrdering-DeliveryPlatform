import { humanize } from '../utils/format';

/** Status + date range filter bar shared by all dashboards. */
export default function OrderFilters({ filters, onChange, statuses, showDates = true }) {
  const set = (k) => (e) => onChange({ ...filters, [k]: e.target.value });
  const hasFilters = filters.status || filters.date_from || filters.date_to;
  return (
    <div className="filters">
      <label>
        <span>Status</span>
        <select value={filters.status || ''} onChange={set('status')}>
          <option value="">All statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
        </select>
      </label>
      {showDates && (
        <>
          <label>
            <span>From</span>
            <input type="date" value={filters.date_from || ''} max={filters.date_to || undefined} onChange={set('date_from')} />
          </label>
          <label>
            <span>To</span>
            <input type="date" value={filters.date_to || ''} min={filters.date_from || undefined} onChange={set('date_to')} />
          </label>
        </>
      )}
      {hasFilters && (
        <button className="btn btn-ghost btn-sm" onClick={() => onChange({ status: '', date_from: '', date_to: '' })}>
          Clear filters
        </button>
      )}
    </div>
  );
}
