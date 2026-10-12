/**
 * VerifyEmailPage — Email Verification Confirmation
 * ==================================================
 * Handles the email verification callback.
 * Auto-verifies using the token from the URL, then redirects to dashboard.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'motion/react';
import '../styles/VerifyEmailPage.css';
import tavixLogo from '../assets/tavix-guard-logo.png';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export default function VerifyEmailPage({ onVerified }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [error, setError] = useState('');
  const [jwtToken, setJwtToken] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');

      if (!token) {
        setStatus('error');
        setError('Verification token is missing from the URL');
        return;
      }

      try {
        const response = await fetch(
          `${BACKEND_URL}/api/auth/verify-email?token=${encodeURIComponent(token)}`
        );

        const data = await response.json();

        if (!response.ok) {
          setStatus('error');
          setError(data.detail || 'Verification failed');
          return;
        }

        // Verification successful
        setStatus('success');
        setJwtToken(data.jwt_token);

        // Call the callback to update auth state
        if (onVerified) {
          onVerified(data.jwt_token);
        }

        // Redirect to dashboard after 1.5 seconds
        const timer = setTimeout(() => {
          navigate('/dashboard');
        }, 1500);

        return () => clearTimeout(timer);
      } catch (err) {
        console.error('Verification error:', err);
        setStatus('error');
        setError('An error occurred during verification');
      }
    };

    verifyEmail();
  }, [searchParams, navigate, onVerified]);

  return (
    <div className="verify-page">
      <div className="verify-bg-gradient" />

      <motion.div
        className="verify-container"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Logo */}
        <div className="verify-logo-section">
          <img src={tavixLogo} alt="TAVIX GUARD" className="verify-logo-img" />
          <div className="verify-logo-text">
            <h1>TAVIX GUARD</h1>
          </div>
        </div>

        {/* Verifying State */}
        {status === 'verifying' && (
          <motion.div
            className="verify-state verifying"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <div className="spinner-large" />
            <h2>Verifying your email...</h2>
            <p>Please wait while we confirm your email address.</p>
          </motion.div>
        )}

        {/* Success State */}
        {status === 'success' && (
          <motion.div
            className="verify-state success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <motion.div
              className="success-icon"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            >
              ✓
            </motion.div>
            <h2>Email verified successfully!</h2>
            <p>Welcome to TAVIX GUARD. Redirecting to dashboard...</p>
            <div className="redirect-countdown">
              <span>Redirecting in</span>
              <motion.span
                className="countdown"
                initial={{ opacity: 1 }}
                animate={{ opacity: [1, 0.5] }}
                transition={{ repeat: Infinity, duration: 1 }}
              >
                3 seconds
              </motion.span>
            </div>
          </motion.div>
        )}

        {/* Error State */}
        {status === 'error' && (
          <motion.div
            className="verify-state error"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <div className="error-icon">✕</div>
            <h2>Verification failed</h2>
            <p className="error-text">{error}</p>
            <div className="error-actions">
              <button
                onClick={() => navigate('/login')}
                className="btn-back-to-login"
              >
                Back to Login
              </button>
              <p className="error-help">
                The verification link may have expired. Please request a new one.
              </p>
            </div>
          </motion.div>
        )}

        {/* Footer */}
        <div className="verify-footer">
          <p>&copy; 2025 TAVIX GUARD. All rights reserved.</p>
        </div>
      </motion.div>
    </div>
  );
}
