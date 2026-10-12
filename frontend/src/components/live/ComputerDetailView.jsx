import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { BACKEND_URL } from '../../useAuthSentinel';
import CustomSelect from '../CustomSelect';
import './ComputerDetailView.css';

const formatAuthResult = (status) => {
  const normalizedStatus = String(status || '').toUpperCase();
  if (normalizedStatus === 'SUCCESS') return 'SUCCESS';
  if (normalizedStatus === 'FAILURE' || normalizedStatus === 'FAILED') return 'FAILED';
  return status || 'UNKNOWN';
};

export default function ComputerDetailView({
  terminalId,
  lab,
  onBackToComputers,
  onGoToLabs,
}) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [logFilter, setLogFilter] = useState('ALL');
  const [logSearch, setLogSearch] = useState('');
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [expandedIncident, setExpandedIncident] = useState(null);
  const [evPage, setEvPage] = useState(1);
  const EV_PAGE_SIZE = 25;

  const fetchDetail = useCallback(async (isInitial = false) => {
    if (!terminalId) return;
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/computers/${encodeURIComponent(terminalId)}`);
      if (!res.ok) {
        throw new Error(`Failed to load system details for ${terminalId}: ${res.statusText}`);
      }
      const data = await res.json();
      setDetail(data);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Error fetching computer detail:', err);
      setError(err.message || 'Unable to fetch system information.');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [terminalId]);

  useEffect(() => {
    fetchDetail(true);
    const interval = setInterval(() => {
      fetchDetail(false);
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchDetail]);

  useEffect(() => {
    setEvPage(1);
  }, [logSearch, logFilter]);

  const comp = detail?.computer;
  const labInfo = detail?.lab || lab;
  const authEvents = detail?.auth_events || [];
  const incidents = detail?.incidents || [];

  // Deduplicate incidents by ID
  const uniqueIncidents = useMemo(() => {
    const seen = new Set();
    return incidents.filter((inc) => {
      if (seen.has(inc.id)) return false;
      seen.add(inc.id);
      return true;
    });
  }, [incidents]);

  // Deduplicate auth events by ID or composite key
  const uniqueEvents = useMemo(() => {
    const seen = new Set();
    return authEvents.filter((ev) => {
      const key = ev.id ? String(ev.id) : `${ev.event_id}-${ev.timestamp}-${ev.username}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [authEvents]);

  // Filter auth event logs
  const filteredEvents = useMemo(() => {
    return uniqueEvents.filter((ev) => {
      const q = logSearch.trim().toLowerCase();
      const matchesSearch =
        !q ||
        (ev.username && ev.username.toLowerCase().includes(q)) ||
        (ev.source_ip && ev.source_ip.toLowerCase().includes(q)) ||
        (ev.source_host && ev.source_host.toLowerCase().includes(q)) ||
        String(ev.event_id).includes(q);

      const matchesStatus =
        logFilter === 'ALL' ||
        (ev.status && ev.status.toUpperCase() === logFilter.toUpperCase());

      return matchesSearch && matchesStatus;
    });
  }, [uniqueEvents, logSearch, logFilter]);

  const getStatusBadge = (status) => {
    const s = status || 'Unknown';
    if (s === 'Online') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 10px',
            borderRadius: '999px',
            fontSize: '11px',
            fontWeight: 700,
            background: '#ecfdf5',
            color: '#059669',
            border: '1px solid #a7f3d0',
          }}
        >
          ONLINE
        </span>
      );
    }
    if (s === 'Offline') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 10px',
            borderRadius: '999px',
            fontSize: '11px',
            fontWeight: 700,
            background: '#fef2f2',
            color: '#dc2626',
            border: '1px solid #fecaca',
          }}
        >
          OFFLINE
        </span>
      );
    }
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 10px',
          borderRadius: '999px',
          fontSize: '11px',
          fontWeight: 700,
          background: '#f3f4f6',
          color: '#6b7280',
          border: '1px solid #e5e7eb',
        }}
      >
        Unknown
      </span>
    );
  };

  const renderValue = (val, isMono = false) => {
    if (!val || val === '—' || val === '-') {
      return (
        <span style={{ color: 'var(--text-tertiary)', fontStyle: 'italic', fontSize: '13px' }}>
          Not available
        </span>
      );
    }
    return (
      <span
        style={{
          color: 'var(--text-primary)',
          fontWeight: 600,
          fontFamily: isMono ? 'var(--font-mono)' : 'inherit',
          fontSize: isMono ? '13px' : '14px',
        }}
      >
        {val}
      </span>
    );
  };

  return (
    <div className="section" style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* ── Breadcrumb & Back Navigation ─────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          paddingBottom: '14px',
          borderBottom: '1px solid var(--border-light)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={onGoToLabs}
            id="breadcrumb-labs-link"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent)',
              fontWeight: 600,
              cursor: 'pointer',
              padding: '2px 4px',
            }}
          >
            Laboratories
          </button>
          <span style={{ color: 'var(--text-tertiary)' }}>›</span>
          <button
            type="button"
            onClick={onBackToComputers}
            id="breadcrumb-lab-name-link"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent)',
              fontWeight: 600,
              cursor: 'pointer',
              padding: '2px 4px',
            }}
          >
            {labInfo?.name || 'Lab'}
          </button>
          <span style={{ color: 'var(--text-tertiary)' }}>›</span>
          <button
            type="button"
            onClick={onBackToComputers}
            id="breadcrumb-connected-computers-link"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent)',
              fontWeight: 600,
              cursor: 'pointer',
              padding: '2px 4px',
            }}
          >
            Connected Computers
          </button>
          <span style={{ color: 'var(--text-tertiary)' }}>›</span>
          <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
            {comp?.computer_name || comp?.hostname || terminalId}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
            Updated: {lastRefreshed.toLocaleTimeString()}
          </span>
          <button
            type="button"
            onClick={onBackToComputers}
            id="btn-back-to-computers"
            className="btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            <span>Back to Connected Computers</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div
          style={{
            padding: '70px 24px',
            textAlign: 'center',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border-light)',
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              border: '3px solid var(--border-normal)',
              borderTopColor: 'var(--accent)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 16px auto',
            }}
          />
          <h4 style={{ fontSize: '16px', color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
            Loading system details for {terminalId}...
          </h4>
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', margin: 0 }}>
            Fetching hardware specifications, telemetry, and security events
          </p>
        </div>
      ) : error ? (
        <div
          style={{
            padding: '40px 24px',
            textAlign: 'center',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-xl)',
          }}
        >
          <div style={{ fontSize: '28px', marginBottom: '8px' }}>⚠️</div>
          <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#b91c1c', margin: '0 0 8px 0' }}>
            Failed to Load System Details
          </h4>
          <p style={{ fontSize: '13px', color: '#dc2626', margin: '0 0 16px 0' }}>
            {error}
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => fetchDetail(true)}
            style={{ padding: '8px 18px', fontSize: '13px' }}
          >
            Retry
          </button>
        </div>
      ) : !comp ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
          Computer details not found.
        </div>
      ) : (
        <>
          {/* ── Compact Header & Security Summary (Fits Above the Fold) ── */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '14px',
            }}
          >
            {/* Card 1: Compact Computer Information Header */}
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-lg)',
                padding: '16px 18px',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '12px',
              }}
            >
              {/* Header row: Hostname, Terminal ID, Status */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div
                    style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--accent-light)',
                      color: 'var(--accent)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                      <line x1="8" y1="21" x2="16" y2="21" />
                      <line x1="12" y1="17" x2="12" y2="21" />
                    </svg>
                  </div>
                  <div>
                    <h2
                      style={{
                        fontSize: '16px',
                        fontWeight: 800,
                        margin: 0,
                        color: 'var(--text-primary)',
                        lineHeight: 1.2,
                      }}
                    >
                      {comp.hostname || comp.computer_name || comp.terminal_id}
                    </h2>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: 'var(--text-tertiary)',
                      }}
                    >
                      Terminal ID: {comp.terminal_id}
                    </span>
                  </div>
                </div>

                <div>{getStatusBadge(comp.status)}</div>
              </div>

              {/* Compact horizontal grid of required fields */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '8px 12px',
                  background: 'var(--bg-secondary)',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-light)',
                  fontSize: '12px',
                }}
              >
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    IP Address
                  </div>
                  <div>{renderValue(comp.ip_address, true)}</div>
                </div>

                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Logged-in User
                  </div>
                  <div>{renderValue(comp.logged_in_user)}</div>
                </div>

                <div style={{ gridColumn: 'span 2' }}>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Last Seen Timestamp
                  </div>
                  <div>{renderValue(comp.last_seen_formatted, true)}</div>
                </div>
              </div>
            </div>

            {/* Card 2: Security & Last Auth Event (Compact Card) */}
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-lg)',
                padding: '16px 18px',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '12px',
              }}
            >
              {/* Header row: Security title & Active incident badge */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                    Security & Last Auth Event
                  </h3>
                </div>

                <div>
                  {uniqueIncidents.length > 0 && (
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '2px 8px',
                        borderRadius: '999px',
                        fontSize: '11px',
                        fontWeight: 700,
                        background: '#fee2e2',
                        color: '#dc2626',
                        border: '1px solid #fecaca',
                      }}
                    >
                      {uniqueIncidents.length} Active Alert{uniqueIncidents.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>

              {/* Compact Security & Event fields */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '8px 12px',
                  background: 'var(--bg-secondary)',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-light)',
                  fontSize: '12px',
                }}
              >
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Event ID
                  </div>
                  <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    {comp.last_auth_event ? String(comp.last_auth_event.event_id) : 'Not available'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Result
                  </div>
                  <div>
                    {comp.last_auth_event ? (
                      <span
                        style={{
                          display: 'inline-flex',
                          padding: '2px 8px',
                          borderRadius: '999px',
                          fontSize: '11px',
                          fontWeight: 700,
                          background: String(comp.last_auth_event.status).toUpperCase() === 'SUCCESS' ? '#ecfdf5' : '#fee2e2',
                          color: String(comp.last_auth_event.status).toUpperCase() === 'SUCCESS' ? '#059669' : '#dc2626',
                          border: String(comp.last_auth_event.status).toUpperCase() === 'SUCCESS' ? '1px solid #a7f3d0' : '1px solid #fecaca',
                        }}
                      >
                        {formatAuthResult(comp.last_auth_event.status)}
                      </span>
                    ) : (
                      renderValue(null)
                    )}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Auth Account
                  </div>
                  <div>{renderValue(comp.last_auth_event?.username)}</div>
                </div>

                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Risk Level
                  </div>
                  <div>
                    {comp.last_auth_event ? (
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: '11px',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background:
                            comp.last_auth_event.risk_level === 'HIGH'
                              ? '#fee2e2'
                              : comp.last_auth_event.risk_level === 'MEDIUM'
                              ? '#fef3c7'
                              : '#ecfdf5',
                          color:
                            comp.last_auth_event.risk_level === 'HIGH'
                              ? '#dc2626'
                              : comp.last_auth_event.risk_level === 'MEDIUM'
                              ? '#d97706'
                              : '#059669',
                        }}
                      >
                        {comp.last_auth_event.risk_level || 'LOW'}
                      </span>
                    ) : (
                      renderValue(null)
                    )}
                  </div>
                </div>

                <div style={{ gridColumn: 'span 2' }}>
                  <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '2px' }}>
                    Event Timestamp
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                    {comp.last_auth_event?.timestamp
                      ? new Date(comp.last_auth_event.timestamp).toLocaleString('en-GB')
                      : 'Not available'}
                  </div>
                </div>
              </div>

              {/* Pattern note for SUCCESS_AFTER_FAILURES */}
              {comp.last_auth_event?.status === 'SUCCESS' &&
                uniqueIncidents.some(
                  (inc) =>
                    inc.alert_type &&
                    inc.alert_type.toUpperCase().includes('SUCCESS_AFTER_FAILURES')
                ) && (
                  <div
                    style={{
                      background: '#fffbeb',
                      border: '1px solid #fde68a',
                      borderRadius: 'var(--radius-md)',
                      padding: '10px 12px',
                      fontSize: '12px',
                      color: '#92400e',
                      marginTop: '8px',
                    }}
                  >
                    ⚠ <strong>Suspicious pattern:</strong> Successful login following failed attempts
                  </div>
                )}
            </div>
          </div>

          {/* ── Related Security Incidents & Alerts Section ─────────── */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-lg)',
              padding: '16px 20px',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 2px 0', color: 'var(--text-primary)' }}>
                  Related Security Incidents & Alerts ({uniqueIncidents.length})
                </h3>
              </div>
            </div>

            {uniqueIncidents.length === 0 ? (
              <div
                style={{
                  padding: '24px 16px',
                  textAlign: 'center',
                  background: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                }}
              >
                <span style={{ color: '#10b981', fontWeight: 700, marginRight: '6px' }}>✓</span>
                No active security incidents or alerts detected for this computer.
              </div>
            ) : (
              <div className="data-table-container" style={{ overflowX: 'auto' }}>
                <table className="data-table" style={{ fontSize: '12px', width: '100%' }}>
                  <thead>
                    <tr>
                      <th style={{ padding: '8px 10px' }}>Incident</th>
                      <th style={{ padding: '8px 10px' }}>Severity</th>
                      <th style={{ padding: '8px 10px' }}>Account</th>
                      <th style={{ padding: '8px 10px' }}>Failed attempts</th>
                      <th style={{ padding: '8px 10px' }}>Detected at</th>
                      <th style={{ padding: '8px 10px' }}>Status</th>
                      <th style={{ padding: '8px 10px' }}>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {uniqueIncidents.map((inc) => (
                      <React.Fragment key={inc.id}>
                        <tr>
                          <td style={{ padding: '8px 10px' }}>
                            <div style={{ fontWeight: 700, fontSize: '12px', color: 'var(--text-primary)' }}>
                              {inc.alert_type === 'SUCCESS_AFTER_FAILURES'
                                ? 'Successful login after 3 failed attempts'
                                : inc.alert_type === 'BRUTE_FORCE'
                                ? 'Brute force attack detected'
                                : inc.alert_type === 'MULTIPLE_FAILURES'
                                ? 'Multiple authentication failures'
                                : inc.alert_type === 'ACCOUNT_LOCKOUT'
                                ? 'Account lockout triggered'
                                : (inc.alert_type || '—').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                            </div>
                            <div
                              style={{
                                fontFamily: 'var(--font-mono)',
                                fontSize: '10px',
                                color: 'var(--text-tertiary)',
                                marginTop: '2px',
                              }}
                            >
                              {inc.alert_type}
                            </div>
                          </td>
                          <td style={{ padding: '8px 10px' }}>
                            <span
                              style={{
                                display: 'inline-flex',
                                padding: '2px 8px',
                                borderRadius: '999px',
                                fontSize: '10px',
                                fontWeight: 700,
                                background:
                                  inc.risk_level === 'CRITICAL'
                                    ? '#fee2e2'
                                    : inc.risk_level === 'HIGH'
                                    ? '#fee2e2'
                                    : inc.risk_level === 'MEDIUM'
                                    ? '#fef3c7'
                                    : '#ecfdf5',
                                color:
                                  inc.risk_level === 'CRITICAL'
                                    ? '#b91c1c'
                                    : inc.risk_level === 'HIGH'
                                    ? '#dc2626'
                                    : inc.risk_level === 'MEDIUM'
                                    ? '#d97706'
                                    : '#059669',
                                border:
                                  inc.risk_level === 'CRITICAL'
                                    ? '1px solid #fecaca'
                                    : inc.risk_level === 'HIGH'
                                    ? '1px solid #fecaca'
                                    : inc.risk_level === 'MEDIUM'
                                    ? '1px solid #fcd34d'
                                    : '1px solid #a7f3d0',
                              }}
                            >
                              {inc.risk_level === 'CRITICAL'
                                ? 'Critical'
                                : inc.risk_level === 'HIGH'
                                ? 'High'
                                : inc.risk_level === 'MEDIUM'
                                ? 'Medium'
                                : 'Low'}
                            </span>
                          </td>
                          <td style={{ padding: '8px 10px', fontWeight: 600 }}>
                            {inc.username || '—'}
                          </td>
                          <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>
                            {inc.failure_count || 1}
                          </td>
                          <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                            {inc.triggered_at
                              ? new Date(inc.triggered_at).toLocaleString('en-GB')
                              : '—'}
                          </td>
                          <td style={{ padding: '8px 10px' }}>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '2px 8px',
                                borderRadius: '999px',
                                background:
                                  inc.status === 'RESOLVED' ? '#ecfdf5' : inc.status === 'OPEN' ? '#fee2e2' : '#f3f4f6',
                                color:
                                  inc.status === 'RESOLVED' ? '#059669' : inc.status === 'OPEN' ? '#dc2626' : '#6b7280',
                                border:
                                  inc.status === 'RESOLVED'
                                    ? '1px solid #a7f3d0'
                                    : inc.status === 'OPEN'
                                    ? '1px solid #fecaca'
                                    : '1px solid #e5e7eb',
                              }}
                            >
                              {inc.status || (inc.resolved ? 'RESOLVED' : 'OPEN')}
                            </span>
                          </td>
                          <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                            <button
                              type="button"
                              onClick={() =>
                                setExpandedIncident(expandedIncident === inc.id ? null : inc.id)
                              }
                              style={{
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                color: 'var(--accent)',
                                fontWeight: 600,
                                fontSize: '11px',
                                padding: '2px 4px',
                              }}
                            >
                              {expandedIncident === inc.id ? '▼ Hide' : '▶ Show'}
                            </button>
                          </td>
                        </tr>
                        {expandedIncident === inc.id && (
                          <tr>
                            <td colSpan="7" style={{ padding: '0' }}>
                              <div
                                style={{
                                  background: 'var(--bg-secondary)',
                                  borderTop: '1px solid var(--border-light)',
                                  padding: '12px 16px',
                                  fontSize: '12px',
                                  color: 'var(--text-secondary)',
                                  lineHeight: 1.5,
                                }}
                              >
                                <strong style={{ color: 'var(--text-primary)' }}>Detection Details:</strong>
                                <div style={{ marginTop: '6px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                                  {inc.reason || 'Threshold-based detection triggered'}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ── Authentication Event Logs History Section ───────────── */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-lg)',
              padding: '16px 20px',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px',
                marginBottom: '12px',
              }}
            >
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 2px 0', color: 'var(--text-primary)' }}>
                  Authentication Event Logs History ({filteredEvents.length})
                </h3>
              </div>

              {/* Log Search & Filter Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  placeholder="Filter logs by user or IP..."
                  value={logSearch}
                  onChange={(e) => setLogSearch(e.target.value)}
                  style={{
                    padding: '5px 10px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-normal)',
                    fontSize: '11px',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    outline: 'none',
                    minWidth: '170px',
                  }}
                />

                <CustomSelect
                  value={logFilter}
                  onChange={(e) => setLogFilter(e.target.value)}
                  options={[
                    { value: 'ALL', label: 'All Events' },
                    { value: 'SUCCESS', label: 'Success Only' },
                    { value: 'FAILURE', label: 'Failures Only' },
                  ]}
                  placeholder="Filter logs..."
                  style={{ minWidth: '140px' }}
                />
              </div>
            </div>

            <div className="data-table-container" style={{ overflowX: 'auto' }}>
              <table className="data-table" style={{ fontSize: '12px', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '8px 10px' }}>Timestamp</th>
                    <th style={{ padding: '8px 10px' }}>Event ID</th>
                    <th style={{ padding: '8px 10px' }}>Account</th>
                    <th style={{ padding: '8px 10px' }}>Login Result</th>
                    <th style={{ padding: '8px 10px' }}>Source</th>
                    <th style={{ padding: '8px 10px' }}>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)' }}>
                        {uniqueEvents.length === 0
                          ? 'No authentication events recorded for this computer.'
                          : 'No events match the current filter.'}
                      </td>
                    </tr>
                  ) : (
                    filteredEvents
                      .slice((evPage - 1) * EV_PAGE_SIZE, evPage * EV_PAGE_SIZE)
                      .map((ev) => (
                        <tr key={ev.id || `${ev.event_id}-${ev.timestamp}-${ev.username}`}>
                          <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleString('en-GB') : '—'}
                          </td>
                          <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                            {ev.event_id || '—'}
                          </td>
                          <td style={{ padding: '8px 10px', fontWeight: 600 }}>{ev.username || '—'}</td>
                          <td style={{ padding: '8px 10px' }}>
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '2px 8px',
                                borderRadius: '999px',
                                fontWeight: 700,
                                fontSize: '11px',
                                background: String(ev.status).toUpperCase() === 'SUCCESS' ? '#ecfdf5' : '#fee2e2',
                                color: String(ev.status).toUpperCase() === 'SUCCESS' ? '#059669' : '#dc2626',
                                border: String(ev.status).toUpperCase() === 'SUCCESS' ? '1px solid #a7f3d0' : '1px solid #fecaca',
                              }}
                            >
                              {formatAuthResult(ev.status)}
                            </span>
                          </td>
                          <td style={{ padding: '8px 10px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                            <div style={{ fontFamily: 'var(--font-mono)' }}>{ev.source_ip || 'Local'}</div>
                            {ev.source_host && ev.source_host !== ev.source_ip && (
                              <div
                                style={{
                                  fontFamily: 'var(--font-mono)',
                                  fontSize: '10px',
                                  color: 'var(--text-tertiary)',
                                  marginTop: '1px',
                                }}
                              >
                                {ev.source_host}
                              </div>
                            )}
                          </td>
                          <td style={{ padding: '8px 10px' }}>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '2px 6px',
                                borderRadius: '4px',
                                background:
                                  ev.risk_level === 'HIGH'
                                    ? '#fee2e2'
                                    : ev.risk_level === 'MEDIUM'
                                    ? '#fef3c7'
                                    : '#ecfdf5',
                                color:
                                  ev.risk_level === 'HIGH'
                                    ? '#dc2626'
                                    : ev.risk_level === 'MEDIUM'
                                    ? '#d97706'
                                    : '#059669',
                              }}
                            >
                              {ev.risk_level || 'LOW'}
                            </span>
                          </td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {filteredEvents.length > EV_PAGE_SIZE && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  marginTop: '12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                }}
              >
                <button
                  type="button"
                  onClick={() => setEvPage((p) => Math.max(1, p - 1))}
                  disabled={evPage === 1}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: evPage === 1 ? 'var(--text-tertiary)' : 'var(--accent)',
                    cursor: evPage === 1 ? 'default' : 'pointer',
                    fontWeight: 600,
                    fontSize: '12px',
                  }}
                >
                  ← Prev
                </button>
                <span style={{ fontWeight: 600 }}>
                  Page {evPage} of {Math.ceil(filteredEvents.length / EV_PAGE_SIZE)}
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setEvPage((p) => Math.min(Math.ceil(filteredEvents.length / EV_PAGE_SIZE), p + 1))
                  }
                  disabled={evPage === Math.ceil(filteredEvents.length / EV_PAGE_SIZE)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: evPage === Math.ceil(filteredEvents.length / EV_PAGE_SIZE) ? 'var(--text-tertiary)' : 'var(--accent)',
                    cursor: evPage === Math.ceil(filteredEvents.length / EV_PAGE_SIZE) ? 'default' : 'pointer',
                    fontWeight: 600,
                    fontSize: '12px',
                  }}
                >
                  Next →
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
