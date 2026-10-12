/**
 * TAVIX GUARD — Main App Router
 * ================================
 * Routes and Administrator Authentication.
 */

import { Routes, Route, Navigate } from 'react-router-dom';
import { MotionConfig } from 'motion/react';

import Dashboard from './Dashboard';
import LoginPage from './pages/LoginPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import { DateProvider } from './dateFilterUtils';
import { useAuth } from './useAuth';

export default function App() {
  const { token, user, isLoading, isAuthenticated, login, logout, updateUser } = useAuth();

  const handleLogin = (jwtToken) => {
    login(jwtToken);
  };

  const handleLogout = () => {
    logout();
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#0b0f19', color: '#94a3b8' }}>
        Loading session...
      </div>
    );
  }

  return (
    <MotionConfig reducedMotion="user">
      <Routes>
        {/* Root redirect: if authenticated -> dashboard, else -> login */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        {/* Auth routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage onLogin={handleLogin} />
            )
          }
        />
        <Route
          path="/verify-email"
          element={<VerifyEmailPage onVerified={handleLogin} />}
        />

        {/* Protected Dashboard */}
        <Route
          path="/dashboard/*"
          element={
            isAuthenticated ? (
              <DateProvider>
                <Dashboard
                  user={user}
                  token={token}
                  onLogout={handleLogout}
                  onUpdateUser={updateUser}
                />
              </DateProvider>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        {/* Catch-all */}
        <Route
          path="*"
          element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />}
        />
      </Routes>
    </MotionConfig>
  );
}
