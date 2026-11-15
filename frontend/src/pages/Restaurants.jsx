import { useState } from 'react';
import { Link } from 'react-router-dom';
import { restaurantApi } from '../api/services';
import { Alert, EmptyState, Loader, Stars, VegMark } from '../components/Common';
import Pagination from '../components/Pagination';
import { useApi, useDebounce } from '../hooks/useApi';
import { cuisineEmoji, formatCurrency } from '../utils/format';

function RestaurantCard({ r }) {
  return (
    <Link to={`/restaurants/${r.id}`} className={`card restaurant-card ${r.is_open ? '' : 'closed'}`}>
      <div className="restaurant-cover" aria-hidden="true">
        {r.image_url ? <img src={r.image_url} alt="" /> : <span>{cuisineEmoji(r.cuisine)}</span>}
      </div>
      <div className="restaurant-info">
        <h3>{r.name}</h3>
        <p className="muted small">{r.cuisine || 'Multi-cuisine'} · {r.address || 'On campus'}</p>
        <div className="row-between">
          {r.review_count ? (
            <span className="small"><Stars value={r.avg_rating} /> {r.avg_rating} ({r.review_count})</span>
          ) : <span className="small muted">No reviews yet</span>}
          {!r.is_open && <span className="badge status-cancelled">Closed</span>}
        </div>
      </div>
    </Link>
  );
}

function DishSearch() {
  const [q, setQ] = useState('');
  const [minPrice, setMin] = useState('');
  const [maxPrice, setMax] = useState('');
  const [sort, setSort] = useState('price_asc');
  const [page, setPage] = useState(1);
  const dq = useDebounce(q);
  const dMin = useDebounce(minPrice);
  const dMax = useDebounce(maxPrice);
  const { data, loading, error } = useApi(
    () => restaurantApi.searchDishes({ q: dq, min_price: dMin, max_price: dMax, sort, page, page_size: 12 }),
    [dq, dMin, dMax, sort, page],
  );
  const reset = (fn) => (e) => { fn(e.target.value); setPage(1); };

  return (
    <>
      <div className="filters">
        <label className="grow"><span>Dish name</span><input type="search" placeholder="e.g. burger, momos…" value={q} onChange={reset(setQ)} /></label>
        <label><span>Min ₹</span><input type="number" min="0" value={minPrice} onChange={reset(setMin)} /></label>
        <label><span>Max ₹</span><input type="number" min="0" value={maxPrice} onChange={reset(setMax)} /></label>
        <label><span>Sort</span>
          <select value={sort} onChange={reset(setSort)}>
            <option value="price_asc">Price: low → high</option>
            <option value="price_desc">Price: high → low</option>
            <option value="name">Name</option>
          </select>
        </label>
      </div>
      <Alert>{error}</Alert>
      {loading ? <Loader /> : data?.items.length ? (
        <div className="grid dish-grid">
          {data.items.map((d) => (
            <Link key={d.id} to={`/restaurants/${d.restaurant_id}?q=${encodeURIComponent(d.name)}`} className="card dish-result">
              <div><VegMark veg={d.is_veg} /> <strong>{d.name}</strong></div>
              <div className="muted small">{d.restaurant_name}</div>
              <div className="price">{formatCurrency(d.price)}</div>
            </Link>
          ))}
        </div>
      ) : <EmptyState icon="🔍" title="No dishes match your search" />}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </>
  );
}

export default function Restaurants() {
  const [tab, setTab] = useState('restaurants');
  const [q, setQ] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [page, setPage] = useState(1);
  const dq = useDebounce(q);
  const { data: cuisines } = useApi(() => restaurantApi.cuisines(), []);
  const { data, loading, error, reload } = useApi(
    () => restaurantApi.list({ q: dq, cuisine, page, page_size: 9 }),
    [dq, cuisine, page],
  );

  return (
    <div className="container page">
      <section className="hero">
        <h1>Hungry? Order from campus favourites 🍕</h1>
        <p>Fresh food from campus kitchens, delivered to your hostel or department.</p>
      </section>

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'restaurants'} className={tab === 'restaurants' ? 'active' : ''} onClick={() => setTab('restaurants')}>Restaurants</button>
        <button role="tab" aria-selected={tab === 'dishes'} className={tab === 'dishes' ? 'active' : ''} onClick={() => setTab('dishes')}>Search dishes</button>
      </div>

      {tab === 'dishes' ? <DishSearch /> : (
        <>
          <div className="filters">
            <label className="grow"><span>Search</span>
              <input type="search" placeholder="Restaurant or cuisine…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
            </label>
            <label><span>Cuisine</span>
              <select value={cuisine} onChange={(e) => { setCuisine(e.target.value); setPage(1); }}>
                <option value="">All cuisines</option>
                {(cuisines || []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
          {error && <Alert>{error} <button className="btn btn-ghost btn-sm" onClick={reload}>Retry</button></Alert>}
          {loading ? <Loader text="Finding restaurants…" /> : data?.items.length ? (
            <div className="grid restaurant-grid">
              {data.items.map((r) => <RestaurantCard key={r.id} r={r} />)}
            </div>
          ) : !error && <EmptyState title="No restaurants found">Try a different search.</EmptyState>}
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
        </>
      )}
    </div>
  );
}
