import React, { useState, useEffect } from 'react';
import DateFilter from '../DateFilter';

export default function Header({ health, wsStatus, onExport }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const isWsConnected = wsStatus === 'CONNECTED';
  const isBackendOnline = health?.backend === 'ONLINE';
  const isCollectorConnected = health?.collector_status === 'CONNECTED';

  return (
    <header className="header" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-light)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '0.2px' }}>
            TAVIX GUARD
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', margin: '2px 0 0 0' }}>
            Live Security Monitoring & Real-Time Telemetry
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '999px',
              fontSize: '11px',
              fontWeight: 600,
              background: isWsConnected ? '#ecfdf5' : '#fef2f2',
              color: isWsConnected ? '#059669' : '#dc2626',
              border: `1px solid ${isWsConnected ? '#a7f3d0' : '#fecaca'}`,
            }}
          >
            <span
              className={isWsConnected ? "live-pulse-dot" : ""}
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: isWsConnected ? '#10b981' : '#ef4444',
              }}
            />
            {isWsConnected ? 'LIVE STREAM' : 'OFFLINE'}
          </span>

          <span
            style={{
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 500,
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-light)',
            }}
          >
            Backend: {isBackendOnline ? 'ONLINE' : 'CONNECTING'}
          </span>

          {isCollectorConnected && (
            <span
              style={{
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 500,
                background: '#eff6ff',
                color: '#2563eb',
                border: '1px solid #bfdbfe',
              }}
            >
              Collector: {health?.collector_hostname || 'CONNECTED'}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <DateFilter />
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {time.toLocaleTimeString('en-GB', { hour12: false, timeZone: 'Asia/Kolkata' })}
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={onExport}
          title="Export available live telemetry records to CSV"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '13px', fontWeight: 600 }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>Export Live Telemetry</span>
        </button>
      </div>
    </header>
  );
}
