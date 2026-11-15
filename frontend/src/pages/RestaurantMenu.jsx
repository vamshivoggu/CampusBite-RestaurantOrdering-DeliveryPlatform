import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { restaurantApi } from '../api/services';
import { Alert, EmptyState, Loader, Stars, VegMark } from '../components/Common';
import Pagination from '../components/Pagination';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useApi, useDebounce } from '../hooks/useApi';
import { cuisineEmoji, formatCurrency, formatDate } from '../utils/format';

function QtyControl({ dish, restaurant }) {
  const { quantityOf, addItem, updateQuantity } = useCart();
  const qty = quantityOf(dish.id);
  if (!dish.is_available) return <span className="badge status-cancelled">Unavailable</span>;
  if (!restaurant.is_open) return <span className="muted small">Closed</span>;
  if (!qty) return <button className="btn btn-primary btn-sm" onClick={() => addItem(dish, restaurant)}>Add +</button>;
  return (
    <div className="qty" aria-label={`Quantity of ${dish.name}`}>
      <button onClick={() => updateQuantity(dish.id, qty - 1)} aria-label="Decrease">−</button>
      <span>{qty}</span>
      <button onClick={() => updateQuantity(dish.id, qty + 1)} aria-label="Increase">+</button>
    </div>
  );
}

function Reviews({ restaurantId }) {
  const [page, setPage] = useState(1);
  const { data, loading } = useApi(() => restaurantApi.reviews(restaurantId, { page, page_size: 5 }), [restaurantId, page]);
  if (loading && !data) return <Loader text="Loading reviews…" />;
  if (!data?.items.length) return <p className="muted">No reviews yet.</p>;
  return (
    <div className="reviews">
      {data.items.map((r) => (
        <div key={r.id} className="review">
          <div className="row-between"><strong>{r.customer_name}</strong><Stars value={r.rating} /></div>
          {r.comment && <p>{r.comment}</p>}
          <span className="muted small">{formatDate(r.created_at)}</span>
        </div>
      ))}
      <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
    </div>
  );
}

export default function RestaurantMenu() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const { cart, count, subtotal } = useCart();
  const [filters, setFilters] = useState({ q: searchParams.get('q') || '', min_price: '', max_price: '', category: '', sort: 'name', available_only: false });
  const [page, setPage] = useState(1);
  const dq = useDebounce(filters.q);
  const dMin = useDebounce(filters.min_price);
  const dMax = useDebounce(filters.max_price);

  const { data: restaurant, loading: rLoading, error: rError } = useApi(() => restaurantApi.get(id), [id]);
  const { data: categories } = useApi(() => restaurantApi.categories(id), [id]);
  const { data: menu, loading, error } = useApi(
    () => restaurantApi.menu(id, { q: dq, min_price: dMin, max_price: dMax, category: filters.category, sort: filters.sort, available_only: filters.available_only || '', page, page_size: 20 }),
    [id, dq, dMin, dMax, filters.category, filters.sort, filters.available_only, page],
  );
  const set = (k) => (e) => { setFilters({ ...filters, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }); setPage(1); };
  const canOrder = !user || user.role === 'customer';

  if (rLoading) return <div className="container page"><Loader /></div>;
  if (rError) return <div className="container page"><Alert>{rError}</Alert><Link to="/restaurants">← Back to restaurants</Link></div>;

  return (
    <div className="container page">
      <Link to="/restaurants" className="back-link">← All restaurants</Link>
      <section className="card restaurant-header">
        <div className="restaurant-emoji" aria-hidden="true">{cuisineEmoji(restaurant.cuisine)}</div>
        <div>
          <h1>{restaurant.name} {!restaurant.is_open && <span className="badge status-cancelled">Closed now</span>}</h1>
          <p className="muted">{restaurant.description}</p>
          <p className="small">{restaurant.cuisine} · {restaurant.address}</p>
          {restaurant.review_count > 0 && <p className="small"><Stars value={restaurant.avg_rating} /> {restaurant.avg_rating} · {restaurant.review_count} reviews</p>}
        </div>
      </section>

      {!canOrder && <Alert type="info">You are logged in as a {user.role.replace('_', ' ')}. Log in as a customer to place orders.</Alert>}

      <div className="filters">
        <label className="grow"><span>Search dishes</span><input type="search" placeholder="Dish name…" value={filters.q} onChange={set('q')} /></label>
        <label><span>Min ₹</span><input type="number" min="0" value={filters.min_price} onChange={set('min_price')} /></label>
        <label><span>Max ₹</span><input type="number" min="0" value={filters.max_price} onChange={set('max_price')} /></label>
        <label><span>Category</span>
          <select value={filters.category} onChange={set('category')}>
            <option value="">All</option>
            {(categories || []).map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label><span>Sort</span>
          <select value={filters.sort} onChange={set('sort')}>
            <option value="name">Name</option>
            <option value="price_asc">Price: low → high</option>
            <option value="price_desc">Price: high → low</option>
          </select>
        </label>
        <label className="check"><input type="checkbox" checked={filters.available_only} onChange={set('available_only')} /> Available only</label>
      </div>

      <Alert>{error}</Alert>
      {loading && !menu ? <Loader text="Loading menu…" /> : menu?.items.length ? (
        <div className="menu-list">
          {menu.items.map((d) => (
            <div key={d.id} className={`card menu-item ${d.is_available ? '' : 'unavailable'}`}>
              <div className="menu-item-info">
                <div><VegMark veg={d.is_veg} /> <strong>{d.name}</strong> {d.category && <span className="chip">{d.category}</span>}</div>
                {d.description && <p className="muted small">{d.description}</p>}
                <div className="price">{formatCurrency(d.price)}</div>
              </div>
              {canOrder && <QtyControl dish={d} restaurant={restaurant} />}
            </div>
          ))}
        </div>
      ) : <EmptyState icon="🥡" title="No dishes match these filters" />}
      {menu && <Pagination page={menu.page} pages={menu.pages} total={menu.total} onChange={setPage} />}

      <section className="section">
        <h2>Reviews</h2>
        <Reviews restaurantId={id} />
      </section>

      {canOrder && count > 0 && cart.restaurantId === restaurant.id && (
        <Link to="/cart" className="floating-cart">
          🛒 {count} item{count > 1 ? 's' : ''} · {formatCurrency(subtotal)} <strong>View cart →</strong>
        </Link>
      )}
    </div>
  );
}
