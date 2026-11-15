export const ROLES = {
  CUSTOMER: 'customer',
  OWNER: 'restaurant_owner',
  DELIVERY: 'delivery_partner',
};

export const ROLE_LABELS = {
  customer: 'Customer',
  restaurant_owner: 'Restaurant Owner',
  delivery_partner: 'Delivery Partner',
};

export const ROLE_HOME = {
  customer: '/restaurants',
  restaurant_owner: '/owner/dashboard',
  delivery_partner: '/delivery/dashboard',
};

/** Main happy-path lifecycle, used for the progress tracker. */
export const LIFECYCLE = ['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY', 'DELIVERED'];

export const ORDER_STATUSES = [...LIFECYCLE, 'CANCELLED', 'REFUNDED'];

/** The next action an owner can take for each status (mirrors the backend state machine). */
export const OWNER_NEXT = {
  PLACED: { status: 'ACCEPTED', label: 'Accept order' },
  ACCEPTED: { status: 'PREPARING', label: 'Start preparing' },
  PREPARING: { status: 'READY', label: 'Mark ready' },
};

export const DELIVERY_NEXT = {
  ASSIGNED: { status: 'OUT_FOR_DELIVERY', label: 'Picked up – Out for delivery' },
  OUT_FOR_DELIVERY: { status: 'DELIVERED', label: 'Mark delivered' },
};

export const PAYMENT_METHODS = [
  { value: 'mock_card', label: '💳 Card (dummy)' },
  { value: 'mock_upi', label: '📱 UPI (dummy)' },
  { value: 'mock_wallet', label: '👛 Wallet (dummy)' },
];
