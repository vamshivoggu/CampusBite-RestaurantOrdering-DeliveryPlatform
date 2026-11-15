export default function Pagination({ page, pages, total, onChange }) {
  if (!pages || pages <= 1) return total ? <p className="pagination-info">{total} result{total === 1 ? '' : 's'}</p> : null;
  const nums = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(pages, start + 4);
  for (let i = start; i <= end; i += 1) nums.push(i);
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Prev</button>
      {start > 1 && <span className="muted">…</span>}
      {nums.map((n) => (
        <button
          key={n} className={`btn btn-sm ${n === page ? 'btn-primary' : 'btn-ghost'}`}
          aria-current={n === page ? 'page' : undefined} onClick={() => onChange(n)}
        >{n}</button>
      ))}
      {end < pages && <span className="muted">…</span>}
      <button className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next ›</button>
      <span className="pagination-info">{total} total</span>
    </nav>
  );
}
