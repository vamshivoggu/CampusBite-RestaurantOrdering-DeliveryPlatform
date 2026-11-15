import { useState } from 'react';
import { getErrorMessage } from '../../api/client';
import { ownerApi } from '../../api/services';
import { Alert, EmptyState, Loader, VegMark } from '../../components/Common';
import Modal from '../../components/Modal';
import Pagination from '../../components/Pagination';
import { useApi, useDebounce } from '../../hooks/useApi';
import { formatCurrency } from '../../utils/format';

const BLANK = { name: '', description: '', price: '', category: '', is_veg: true, is_available: true, image_url: '' };

function DishForm({ initial, onClose, onSaved }) {
  const [form, setForm] = useState(initial ? { ...BLANK, ...initial, description: initial.description || '', category: initial.category || '', image_url: initial.image_url || '' } : BLANK);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const save = async () => {
    const price = Number(form.price);
    if (form.name.trim().length < 2) return setError('Name must have at least 2 characters.');
    if (!price || price <= 0) return setError('Price must be greater than 0.');
    const payload = {
      name: form.name.trim(), description: form.description.trim() || null, price,
      category: form.category.trim() || null, is_veg: form.is_veg, is_available: form.is_available, image_url: form.image_url.trim() || null,
    };
    setBusy(true);
    try {
      onSaved(initial ? await ownerApi.updateDish(initial.id, payload) : await ownerApi.addDish(payload));
    } catch (e) {
      setError(getErrorMessage(e));
      setBusy(false);
    }
  };

  return (
    <Modal title={initial ? `Edit ${initial.name}` : 'Add a new dish'} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save dish'}</button></>}>
      <Alert onClose={() => setError('')}>{error}</Alert>
      <div className="grid-2">
        <label className="field"><span>Name *</span><input value={form.name} onChange={set('name')} maxLength={150} /></label>
        <label className="field"><span>Price (₹) *</span><input type="number" min="1" step="0.5" value={form.price} onChange={set('price')} /></label>
        <label className="field"><span>Category</span><input value={form.category} onChange={set('category')} placeholder="e.g. Burgers" maxLength={80} /></label>
        <label className="field"><span>Image URL</span><input value={form.image_url} onChange={set('image_url')} placeholder="https://…" /></label>
        <label className="field full"><span>Description</span><textarea rows={2} value={form.description} onChange={set('description')} maxLength={2000} /></label>
        <label className="check"><input type="checkbox" checked={form.is_veg} onChange={set('is_veg')} /> Vegetarian</label>
        <label className="check"><input type="checkbox" checked={form.is_available} onChange={set('is_available')} /> Available</label>
      </div>
    </Modal>
  );
}

export default function MenuManagement() {
  const [q, setQ] = useState('');
  const [availability, setAvailability] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null); // null | 'new' | dish
  const [error, setError] = useState('');
  const dq = useDebounce(q);
  const { data, setData, loading, error: loadError, reload } = useApi(
    () => ownerApi.menu({ q: dq, available: availability, page, page_size: 10 }),
    [dq, availability, page],
  );

  const replace = (dish) => setData((d) => ({ ...d, items: d.items.map((x) => (x.id === dish.id ? dish : x)) }));

  const toggle = async (dish) => {
    try { replace(await ownerApi.setAvailability(dish.id, !dish.is_available)); } catch (e) { setError(getErrorMessage(e)); }
  };
  const remove = async (dish) => {
    if (!window.confirm(`Delete "${dish.name}"? Past orders keep their history.`)) return;
    try { await ownerApi.deleteDish(dish.id); reload(); } catch (e) { setError(getErrorMessage(e)); }
  };

  return (
    <div className="container page">
      <div className="row-between wrap">
        <h1>Menu management</h1>
        <button className="btn btn-primary" onClick={() => setEditing('new')}>+ Add dish</button>
      </div>
      <div className="filters">
        <label className="grow"><span>Search</span><input type="search" value={q} placeholder="Dish or category…" onChange={(e) => { setQ(e.target.value); setPage(1); }} /></label>
        <label><span>Availability</span>
          <select value={availability} onChange={(e) => { setAvailability(e.target.value); setPage(1); }}>
            <option value="">All</option><option value="true">Available</option><option value="false">Unavailable</option>
          </select>
        </label>
      </div>
      <Alert onClose={() => setError('')}>{error || loadError}</Alert>

      {loading && !data ? <Loader /> : data?.items.length ? (
        <div className="table-wrap card">
          <table className="table responsive">
            <thead><tr><th>Dish</th><th>Category</th><th className="num">Price</th><th>Available</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {data.items.map((d) => (
                <tr key={d.id} className={d.is_available ? '' : 'row-muted'}>
                  <td data-label="Dish"><VegMark veg={d.is_veg} /> <strong>{d.name}</strong>{d.description && <div className="muted small">{d.description}</div>}</td>
                  <td data-label="Category">{d.category || '—'}</td>
                  <td data-label="Price" className="num">{formatCurrency(d.price)}</td>
                  <td data-label="Available">
                    <label className="switch"><input type="checkbox" checked={d.is_available} onChange={() => toggle(d)} aria-label={`Toggle ${d.name} availability`} /><span>{d.is_available ? 'Yes' : 'No'}</span></label>
                  </td>
                  <td className="actions">
                    <button className="btn btn-ghost btn-sm" onClick={() => setEditing(d)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => remove(d)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState icon="🍳" title="No dishes yet">Add your first dish to start receiving orders.</EmptyState>}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}

      {editing && (
        <DishForm
          initial={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={(dish) => { setEditing(null); if (editing === 'new') reload(); else replace(dish); }}
        />
      )}
    </div>
  );
}
