import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { TOKEN_KEY, USER_KEY } from '../api/client';
import { authApi } from '../api/services';

const AuthContext = createContext(null);

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw && localStorage.getItem(TOKEN_KEY) ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser);
  const [sessionMessage, setSessionMessage] = useState('');

  const persist = (data) => {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setUser(data.user);
    setSessionMessage('');
    return data.user;
  };

  const logout = useCallback((message = '') => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
    setSessionMessage(message);
  }, []);

  const login = async (email, password) => persist(await authApi.login(email, password));
  const register = async (payload) => persist(await authApi.register(payload));

  // Global logout when the API reports an expired/invalid token.
  useEffect(() => {
    const handler = (e) => logout(e.detail);
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, [logout]);

  // Re-validate a persisted session once on load.
  useEffect(() => {
    if (localStorage.getItem(TOKEN_KEY)) {
      authApi.me().then((me) => {
        setUser(me);
        localStorage.setItem(USER_KEY, JSON.stringify(me));
      }).catch(() => {});
    }
  }, []);

  const value = useMemo(
    () => ({ user, isAuthenticated: !!user, login, register, logout, sessionMessage, setSessionMessage }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, sessionMessage, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
