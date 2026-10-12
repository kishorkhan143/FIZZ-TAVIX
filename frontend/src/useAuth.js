/**
 * useAuth — Authentication Hook
 * ================================
 * Manages JWT token storage, validation, and user authentication state.
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'tavix_guard_jwt';
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export const useAuth = () => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(STORAGE_KEY);
    if (storedToken) {
      if (isTokenExpired(storedToken)) {
        // Token is expired, clear it
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      } else {
        setToken(storedToken);
        // Fetch user info
        fetchUserInfo(storedToken);
      }
    }
    setIsLoading(false);
  }, []);

  const isTokenExpired = (jwtToken) => {
    try {
      const payload = JSON.parse(atob(jwtToken.split('.')[1]));
      const expiresAt = payload.exp * 1000; // Convert to milliseconds
      return Date.now() > expiresAt;
    } catch (e) {
      return true;
    }
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
      } else if (response.status === 401) {
        // Token is invalid or expired
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error);
    }
  };

  const login = useCallback((jwtToken) => {
    localStorage.setItem(STORAGE_KEY, jwtToken);
    setToken(jwtToken);
    fetchUserInfo(jwtToken);
  }, []);

  const logout = useCallback(() => {
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
