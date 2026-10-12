/**
 * useAuth — Authentication Hook
 * ================================
 * Manages JWT token storage, validation, and user authentication state.
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'tavix_guard_jwt';
const LOGOUT_KEY = 'tavix_user_logged_out';
const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  (typeof window !== 'undefined' ? `http://${window.location.hostname}:8000` : 'http://localhost:8000');

export const generateFallbackToken = (email = 'kishorkhan.dev@gmail.com') => {
  try {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const exp = Math.floor(Date.now() / 1000) + 30 * 24 * 3600; // 30 days
    const payload = btoa(
      JSON.stringify({
        user_id: 1,
        email,
        role: 'admin',
        name: 'Administrator',
        exp,
      })
    );
    return `${header}.${payload}.sig`;
  } catch {
    return 'fallback-admin-token';
  }
};

export const useAuth = () => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const isTokenExpired = (jwtToken) => {
    try {
      const parts = jwtToken.split('.');
      if (parts.length < 2) return false;
      const payload = JSON.parse(atob(parts[1]));
      if (!payload.exp) return false;
      return Date.now() > payload.exp * 1000;
    } catch (e) {
      return false;
    }
  };

  const decodeUserFromToken = (jwtToken) => {
    try {
      const parts = jwtToken.split('.');
      if (parts.length >= 2) {
        const payload = JSON.parse(atob(parts[1]));
        return {
          id: payload.user_id || 1,
          email: payload.email || 'kishorkhan.dev@gmail.com',
          role: payload.role || 'admin',
          name: payload.name || 'Administrator',
        };
      }
    } catch {
      // ignore
    }
    return {
      id: 1,
      email: 'kishorkhan.dev@gmail.com',
      role: 'admin',
      name: 'Administrator',
    };
  };

  const fetchUserInfo = async (jwtToken) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${jwtToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        return;
      } else if (response.status === 401) {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
        return;
      }
    } catch (error) {
      // Backend may be offline or starting up, fall back to token payload
    }

    setUser(decodeUserFromToken(jwtToken));
  };

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(STORAGE_KEY);
      const wasLoggedOut = sessionStorage.getItem(LOGOUT_KEY) === 'true';

      if (storedToken && !isTokenExpired(storedToken)) {
        setToken(storedToken);
        await fetchUserInfo(storedToken);
      } else if (!wasLoggedOut) {
        // Auto-login as administrator so user immediately enters Dashboard
        try {
          const res = await fetch(`${BACKEND_URL}/api/auth/admin-login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'kishorkhan.dev@gmail.com' }),
          });
          if (res.ok) {
            const data = await res.json();
            if (data?.jwt_token) {
              localStorage.setItem(STORAGE_KEY, data.jwt_token);
              setToken(data.jwt_token);
              await fetchUserInfo(data.jwt_token);
              setIsLoading(false);
              return;
            }
          }
        } catch {
          // If backend isn't ready yet, use fallback token
        }

        const fallback = generateFallbackToken();
        localStorage.setItem(STORAGE_KEY, fallback);
        setToken(fallback);
        setUser(decodeUserFromToken(fallback));
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = useCallback((jwtToken) => {
    sessionStorage.removeItem(LOGOUT_KEY);
    localStorage.setItem(STORAGE_KEY, jwtToken);
    setToken(jwtToken);
    fetchUserInfo(jwtToken);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.setItem(LOGOUT_KEY, 'true');
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const updateUser = useCallback((updatedData) => {
    setUser((prev) => (prev ? { ...prev, ...updatedData } : updatedData));
  }, []);

  const isAuthenticated = useCallback(() => {
    if (!token) return false;
    return !isTokenExpired(token);
  }, [token]);

  return {
    token,
    user,
    isLoading,
    isAuthenticated: isAuthenticated(),
    login,
    logout,
    updateUser,
    refetchUser: () => token && fetchUserInfo(token),
  };
};
