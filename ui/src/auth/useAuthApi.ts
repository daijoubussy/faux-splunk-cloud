import { useMemo, useCallback } from 'react';
import axios from 'axios';
import type { AxiosInstance } from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Hook that returns an axios instance configured for authenticated requests.
 *
 * SAML authentication uses HTTP-only cookies, so we just need to ensure
 * credentials are included with requests.
 */
export function useAuthApi(): AxiosInstance {
  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Include cookies for SAML session
    });

    return instance;
  }, []);

  return api;
}

/**
 * Hook that returns an authenticated fetch function.
 *
 * SAML authentication uses HTTP-only cookies, so we just need to ensure
 * credentials are included with requests.
 */
export function useAuthFetch() {
  const authFetch = useCallback(
    async (url: string, options: RequestInit = {}) => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
      };

      const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers,
        credentials: 'include', // Include cookies for SAML session
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Request failed' }));
        throw new Error(error.message || error.detail || 'Request failed');
      }

      return response.json();
    },
    []
  );

  return authFetch;
}

export default useAuthApi;
