import { useCallback, useEffect, useRef, useState } from 'react';
import { getErrorMessage } from '../api/client';

/**
 * Run an async API function and track { data, loading, error }.
 * Re-runs whenever `deps` change; ignores responses from stale requests.
 */
export function useApi(fn, deps = [], { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState('');
  const callId = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(async () => {
    const id = ++callId.current;
    setLoading(true);
    setError('');
    try {
      const result = await fn();
      if (id === callId.current) setData(result);
      return result;
    } catch (err) {
      if (id === callId.current) setError(getErrorMessage(err));
      return null;
    } finally {
      if (id === callId.current) setLoading(false);
    }
  }, deps);

  useEffect(() => {
    if (immediate) run();
  }, [run, immediate]);

  return { data, setData, loading, error, reload: run };
}

/** Debounce a fast-changing value (e.g. a search box). */
export function useDebounce(value, delay = 400) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}
