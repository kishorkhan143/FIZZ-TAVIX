/**
 * ProtectedRoute — Authentication Guard
 * ======================================
 * Wraps routes to check authentication before rendering.
 * Redirects unauthenticated users to login.
 */

import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ isAuthenticated, isLoading, children }) {
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666',
      }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
