/**
 * IncidentPanel: Manage incidents - view, review, reopen.
 */

import React, { useState, useEffect } from 'react';
import { BACKEND_URL, parseUtc } from '../useAuthSentinel';

export default function IncidentPanel() {
  const [incidents, setIncidents] = useState([]);
  const [filter, setFilter] = useState('OPEN');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        setLoading(true);
        const url = `${BACKEND_URL}/api/incidents?status=${filter}`;
        const res = await fetch(url);
        
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();
        setIncidents(data.incidents || []);
      } catch (err) {
        console.error('Error fetching incidents:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchIncidents();
    // Refresh every 30 seconds
    const interval = setInterval(fetchIncidents, 30000);
    return () => clearInterval(interval);
  }, [filter]);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return parseUtc(dateStr).toLocaleString();
  };

  const getRiskColor = (score) => {
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 30) return '#f59e0b';
    return '#10b981';
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Loading...</p>
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

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Incidents</h2>
      
      {/* Filter Buttons */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.5rem' }}>
        {['OPEN', 'COOLED', 'CLOSED'].map(status => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: filter === status ? '#3b82f6' : '#e5e7eb',
              color: filter === status ? 'white' : '#1f2937',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: filter === status ? '600' : '500',
              transition: 'all 0.2s'
            }}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Incidents Table */}
      {incidents.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#f3f4f6' }}>
                <th style={{ textAlign: 'left', padding: '0.75rem', borderBottom: '2px solid #e5e7eb', fontWeight: '600' }}>ID</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', borderBottom: '2px solid #e5e7eb', fontWeight: '600' }}>Entity</th>
                <th style={{ textAlign: 'center', padding: '0.75rem', borderBottom: '2px solid #e5e7eb', fontWeight: '600' }}>Peak Score</th>
                <th style={{ textAlign: 'center', padding: '0.75rem', borderBottom: '2px solid #e5e7eb', fontWeight: '600' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', borderBottom: '2px solid #e5e7eb', fontWeight: '600' }}>Opened</th>
                <th style={{ textAlign: 'center', padding: '0.75rem', borderBottom: '2px solid #e5e7eb', fontWeight: '600' }}>Events</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map(incident => (
                <tr 
                  key={incident.id} 
                  style={{ 
                    borderBottom: '1px solid #e5e7eb',
                    ':hover': { backgroundColor: '#f9fafb' }
                  }}
                >
                  <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {incident.id}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ fontSize: '0.875rem' }}>
                      <strong>{incident.entity_type}</strong>
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      {incident.entity_id}
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                    <div style={{
                      display: 'inline-block',
                      padding: '0.25rem 0.75rem',
                      backgroundColor: getRiskColor(incident.peak_risk_score),
                      color: 'white',
                      borderRadius: '0.25rem',
                      fontWeight: '600',
                      fontSize: '0.875rem'
                    }}>
                      {incident.peak_risk_score}
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                    <div style={{
                      display: 'inline-block',
                      padding: '0.25rem 0.75rem',
                      backgroundColor: incident.status === 'OPEN' ? '#fecaca' : incident.status === 'COOLED' ? '#fed7aa' : '#d1d5db',
                      color: incident.status === 'OPEN' ? '#7f1d1d' : incident.status === 'COOLED' ? '#7c2d12' : '#374151',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      fontWeight: '600'
                    }}>
                      {incident.status}
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>
                    {formatDate(incident.opened_at)}
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.875rem' }}>
                    {incident.event_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          backgroundColor: '#f9fafb',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb',
          color: '#6b7280'
        }}>
          No incidents found
        </div>
      )}
    </div>
  );
}
