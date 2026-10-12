/**
 * Environment: System settings and lab configuration.
 */

import React, { useState, useEffect } from 'react';
import { BACKEND_URL } from '../useAuthSentinel';

export default function Environment() {
  const [config, setConfig] = useState(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${BACKEND_URL}/api/config`);
        
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();
        setConfig(data);
      } catch (err) {
        console.error('Error fetching config:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  const handleSave = async (newConfig) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      setConfig(newConfig);
      setEditing(false);
      alert('Configuration updated and replay triggered');
    } catch (err) {
      console.error('Error saving config:', err);
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Loading configuration...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', color: '#ef4444' }}>
        <p>Error: {error}</p>
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ padding: '2rem' }}>
        <p>Configuration not available</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Lab Environment Settings</h2>
      <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
        Configure risk parameters. Changes trigger re-scoring of all events.
      </p>

      {!editing ? (
        <div>
          <button 
            onClick={() => setEditing(true)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              marginBottom: '1.5rem'
            }}
          >
            Edit Settings
          </button>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '1.5rem'
          }}>
            <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
              <dt style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Decay Half-Life (seconds)</dt>
              <dd style={{ fontSize: '1.25rem', fontWeight: '700', color: '#3b82f6' }}>
                {config.half_life_seconds}
              </dd>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                At this time, decay = 0.5
              </p>
            </div>

            <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
              <dt style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Incident Threshold</dt>
              <dd style={{ fontSize: '1.25rem', fontWeight: '700', color: '#f97316' }}>
                {config.incident_threshold}
              </dd>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                Open incident when score ≥ this
              </p>
            </div>

            <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
              <dt style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Cool Threshold</dt>
              <dd style={{ fontSize: '1.25rem', fontWeight: '700', color: '#10b981' }}>
                {config.cool_threshold}
              </dd>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                Mark COOLED when score &lt; this
              </p>
            </div>

            <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
              <dt style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Lab Hours</dt>
              <dd style={{ fontSize: '1.25rem', fontWeight: '700', color: '#3b82f6' }}>
                {config.lab_hours_start}:00 - {config.lab_hours_end}:00
              </dd>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                Outside: after_hours_success signal fires
              </p>
            </div>

            <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
              <dt style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Timezone</dt>
              <dd style={{ fontSize: '1.25rem', fontWeight: '700', color: '#3b82f6' }}>
                {config.timezone}
              </dd>
            </div>

            <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem', border: '1px solid #e5e7eb' }}>
              <dt style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Lookback Window</dt>
              <dd style={{ fontSize: '1.25rem', fontWeight: '700', color: '#3b82f6' }}>
                {config.lookback_seconds} seconds
              </dd>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', margin: '0.5rem 0 0 0' }}>
                {(config.lookback_seconds / 3600).toFixed(1)} hours
              </p>
            </div>
          </div>

          <p style={{ marginTop: '2rem', fontSize: '0.875rem', color: '#6b7280' }}>
            💡 Tip: Decrease half-life to react faster to recent attacks. Increase to smooth out noise.
          </p>
        </div>
      ) : (
        <div>
          <p style={{ color: '#ef4444', marginBottom: '1rem' }}>
            ⚠️ Configuration updates will re-score all events in the database.
          </p>
          <button 
            onClick={() => handleSave(config)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              marginRight: '0.5rem'
            }}
          >
            Save & Replay
          </button>
          <button 
            onClick={() => setEditing(false)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
