import { Link, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute, { HomeRedirect } from './components/ProtectedRoute';
import Cart from './pages/Cart';
import AIInsights from './pages/customer/AIInsights';
import CustomerDashboard from './pages/customer/CustomerDashboard';
import DeliveryDashboard from './pages/delivery/DeliveryDashboard';
import Login from './pages/Login';
import OrderDetail from './pages/OrderDetail';
import MenuManagement from './pages/owner/MenuManagement';
import OrderManagement from './pages/owner/OrderManagement';
import OwnerDashboard from './pages/owner/OwnerDashboard';
import ReturnRequests from './pages/owner/ReturnRequests';
import Register from './pages/Register';
import RestaurantMenu from './pages/RestaurantMenu';
import Restaurants from './pages/Restaurants';
import { ROLES } from './utils/constants';

const { CUSTOMER, OWNER, DELIVERY } = ROLES;

function Message({ icon, title, text }) {
  return (
    <div className="container page narrow center">
      <div className="empty-icon">{icon}</div>
      <h1>{title}</h1>
      <p className="muted">{text}</p>
      <Link to="/" className="btn btn-primary">Go home</Link>
    </div>
  );
}

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/restaurants" element={<Restaurants />} />
          <Route path="/restaurants/:id" element={<RestaurantMenu />} />
          <Route path="/cart" element={<Cart />} />

          <Route path="/orders/:id" element={<ProtectedRoute><OrderDetail /></ProtectedRoute>} />

          <Route path="/customer/dashboard" element={<ProtectedRoute roles={[CUSTOMER]}><CustomerDashboard /></ProtectedRoute>} />
          <Route path="/customer/insights" element={<ProtectedRoute roles={[CUSTOMER]}><AIInsights /></ProtectedRoute>} />

          <Route path="/owner/dashboard" element={<ProtectedRoute roles={[OWNER]}><OwnerDashboard /></ProtectedRoute>} />
          <Route path="/owner/orders" element={<ProtectedRoute roles={[OWNER]}><OrderManagement /></ProtectedRoute>} />
          <Route path="/owner/menu" element={<ProtectedRoute roles={[OWNER]}><MenuManagement /></ProtectedRoute>} />
          <Route path="/owner/returns" element={<ProtectedRoute roles={[OWNER]}><ReturnRequests /></ProtectedRoute>} />

          <Route path="/delivery/dashboard" element={<ProtectedRoute roles={[DELIVERY]}><DeliveryDashboard /></ProtectedRoute>} />

          <Route path="/unauthorized" element={<Message icon="🚫" title="Access denied" text="Your account role doesn't have access to this page." />} />
          <Route path="*" element={<Message icon="🤷" title="Page not found" text="The page you're looking for doesn't exist." />} />
        </Routes>
      </main>
      <footer className="footer">CampusBite · Demo project – payments are simulated</footer>
    </>
  );
}
