import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { BACKEND_URL } from '../../useAuthSentinel';

export default function LabComputersView({
  lab,
  onBack,
  onSelectComputer,
  onGoToTerminals,
}) {
  const [computers, setComputers] = useState([]);
  const [labSummary, setLabSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const fetchComputers = useCallback(async (isInitial = false) => {
    if (!lab?.id) return;
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/labs/${encodeURIComponent(lab.id)}/computers`);
      if (!res.ok) {
        throw new Error(`Failed to load computers for laboratory: ${res.statusText}`);
      }
      const data = await res.json();
      setComputers(data.computers || []);
      setLabSummary(data);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Error fetching lab computers:', err);
      setError(err.message || 'Unable to fetch connected computers.');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [lab?.id]);

  useEffect(() => {
    fetchComputers(true);
    // Real heartbeat auto-refresh every 15 seconds
    const interval = setInterval(() => {
      fetchComputers(false);
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchComputers]);

  // Filter computers by search query and status
  const filteredComputers = useMemo(() => {
    return computers.filter((comp) => {
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        (comp.hostname && comp.hostname.toLowerCase().includes(q)) ||
        (comp.computer_name && comp.computer_name.toLowerCase().includes(q)) ||
        (comp.terminal_id && comp.terminal_id.toLowerCase().includes(q)) ||
        (comp.ip_address && comp.ip_address.toLowerCase().includes(q));

      const matchesStatus =
        statusFilter === 'ALL' ||
        (comp.status && comp.status.toLowerCase() === statusFilter.toLowerCase());

      return matchesSearch && matchesStatus;
    });
  }, [computers, searchQuery, statusFilter]);

  const counts = useMemo(() => {
    let online = 0;
    let offline = 0;
    let unknown = 0;
    computers.forEach((c) => {
      if (c.status === 'Online') online++;
      else if (c.status === 'Offline') offline++;
      else unknown++;
    });
    return { total: computers.length, online, offline, unknown };
  }, [computers]);

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
        UNKNOWN
      </span>
    );
  };

  const renderValue = (val, isMono = false) => {
    if (!val || val === '—' || val === '-') {
      return (
        <span style={{ color: 'var(--text-tertiary)', fontStyle: 'italic', fontSize: '12px' }}>
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
          fontSize: isMono ? '12px' : '13px',
        }}
      >
        {val}
      </span>
    );
  };

  return (
    <div className="section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Breadcrumb & Navigation Bar ──────────────────────────── */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <button
            type="button"
            onClick={onBack}
            id="breadcrumb-labs-btn"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent)',
              fontWeight: 600,
              cursor: 'pointer',
              padding: '4px 6px',
              borderRadius: '4px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            Laboratories
          </button>
          <span style={{ color: 'var(--text-tertiary)' }}>›</span>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
            {lab?.name || labSummary?.lab_name || lab?.id}
          </span>
          <span style={{ color: 'var(--text-tertiary)' }}>›</span>
          <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
            Connected Computers
          </span>
        </div>

        <button
          type="button"
          onClick={onBack}
          id="btn-back-to-labs"
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
          <span>Back to Laboratories</span>
        </button>
      </div>

      {/* ── Lab Info Header ────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent-light)',
              color: 'var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {lab?.name || labSummary?.lab_name}
            </h2>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 700,
                background: 'var(--accent-light)',
                color: 'var(--accent)',
                padding: '2px 8px',
                borderRadius: '4px',
              }}
            >
              {lab?.id}
            </span>
          </div>
        </div>
      </div>

      {/* ── Search & Filter Controls ───────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          background: 'var(--bg-secondary)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-light)',
        }}
      >
        {/* Search input */}
        <div style={{ position: 'relative', flex: '1', minWidth: '240px', maxWidth: '420px' }}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-tertiary)',
            }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            id="search-computers-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by hostname, terminal ID, or IP..."
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-normal)',
              background: 'var(--bg-primary)',
              fontSize: '13px',
              color: 'var(--text-primary)',
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-tertiary)',
                cursor: 'pointer',
                fontSize: '12px',
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)' }}>
            Filter Status:
          </span>

          <button
            type="button"
            id="filter-all-btn"
            onClick={() => setStatusFilter('ALL')}
            style={{
              padding: '5px 12px',
              borderRadius: '999px',
              fontSize: '12px',
              fontWeight: statusFilter === 'ALL' ? 700 : 500,
              cursor: 'pointer',
              border: statusFilter === 'ALL' ? '1px solid var(--accent)' : '1px solid var(--border-normal)',
              background: statusFilter === 'ALL' ? 'var(--accent)' : 'var(--bg-primary)',
              color: statusFilter === 'ALL' ? '#ffffff' : 'var(--text-secondary)',
              transition: 'all 0.15s',
            }}
          >
            All ({counts.total})
          </button>

          <button
            type="button"
            id="filter-online-btn"
            onClick={() => setStatusFilter('Online')}
            style={{
              padding: '5px 12px',
              borderRadius: '999px',
              fontSize: '12px',
              fontWeight: statusFilter === 'Online' ? 700 : 500,
              cursor: 'pointer',
              border: statusFilter === 'Online' ? '1px solid #10b981' : '1px solid var(--border-normal)',
              background: statusFilter === 'Online' ? '#10b981' : 'var(--bg-primary)',
              color: statusFilter === 'Online' ? '#ffffff' : '#059669',
              transition: 'all 0.15s',
            }}
          >
            Online ({counts.online})
          </button>

          <button
            type="button"
            id="filter-offline-btn"
            onClick={() => setStatusFilter('Offline')}
            style={{
              padding: '5px 12px',
              borderRadius: '999px',
              fontSize: '12px',
              fontWeight: statusFilter === 'Offline' ? 700 : 500,
              cursor: 'pointer',
              border: statusFilter === 'Offline' ? '1px solid #ef4444' : '1px solid var(--border-normal)',
              background: statusFilter === 'Offline' ? '#ef4444' : 'var(--bg-primary)',
              color: statusFilter === 'Offline' ? '#ffffff' : '#dc2626',
              transition: 'all 0.15s',
            }}
          >
            Offline ({counts.offline})
          </button>

          <button
            type="button"
            id="filter-unknown-btn"
            onClick={() => setStatusFilter('Unknown')}
            style={{
              padding: '5px 12px',
              borderRadius: '999px',
              fontSize: '12px',
              fontWeight: statusFilter === 'Unknown' ? 700 : 500,
              cursor: 'pointer',
              border: statusFilter === 'Unknown' ? '1px solid #6b7280' : '1px solid var(--border-normal)',
              background: statusFilter === 'Unknown' ? '#6b7280' : 'var(--bg-primary)',
              color: statusFilter === 'Unknown' ? '#ffffff' : '#6b7280',
              transition: 'all 0.15s',
            }}
          >
            Unknown ({counts.unknown})
          </button>
        </div>
      </div>

      {/* ── Main Content Area ───────────────────────────────────────── */}
      {loading ? (
        <div
          style={{
            padding: '48px 24px',
            textAlign: 'center',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-light)',
          }}
        >
          <div
            style={{
              width: '28px',
              height: '28px',
              border: '3px solid var(--border-normal)',
              borderTopColor: 'var(--accent)',
              borderRadius: '50%',
              animation: 'spin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite',
              margin: '0 auto 12px auto',
            }}
          />
          <h4 style={{ fontSize: '14px', color: 'var(--text-primary)', margin: '0 0 4px 0' }}>
            Loading connected computers...
          </h4>
          <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', margin: 0 }}>
            Fetching inventory and telemetry records
          </p>
        </div>
      ) : error ? (
        <div
          style={{
            padding: '32px 20px',
            textAlign: 'center',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <div style={{ fontSize: '24px', marginBottom: '6px' }}>⚠️</div>
          <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#b91c1c', margin: '0 0 6px 0' }}>
            Failed to Load Computers
          </h4>
          <p style={{ fontSize: '12px', color: '#dc2626', margin: '0 0 14px 0' }}>
            {error}
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => fetchComputers(true)}
            style={{ padding: '6px 16px', fontSize: '12px' }}
          >
            Retry Connection
          </button>
        </div>
      ) : computers.length === 0 ? (
        /* Empty State: No computers assigned to this lab */
        <div
          className="empty-state"
          style={{
            padding: '48px 20px',
            textAlign: 'center',
            background: 'var(--bg-secondary)',
            border: '1px dashed var(--border-normal)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            style={{ color: 'var(--text-tertiary)', marginBottom: '12px' }}
          >
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
            <line x1="8" y1="21" x2="16" y2="21" />
            <line x1="12" y1="17" x2="12" y2="21" />
          </svg>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
            No computers assigned to this laboratory
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', maxWidth: '400px', margin: '0 0 16px 0', lineHeight: 1.5 }}>
            No computers or terminals have been assigned to <strong>{lab?.name}</strong> yet. You can assign terminals to this lab from the Terminals inventory.
          </p>
          {onGoToTerminals && (
            <button
              type="button"
              className="btn-primary"
              onClick={onGoToTerminals}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <span>Go to Terminals Inventory</span>
            </button>
          )}
        </div>
      ) : filteredComputers.length === 0 ? (
        /* Filter returned 0 results */
        <div
          style={{
            padding: '36px 20px',
            textAlign: 'center',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-light)',
          }}
        >
          <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', margin: '0 0 6px 0' }}>
            No computers match your search or filter
          </p>
          <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', margin: '0 0 12px 0' }}>
            Query: "{searchQuery}" • Status: {statusFilter}
          </p>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('ALL');
            }}
            style={{ padding: '5px 12px', fontSize: '11px' }}
          >
            Clear Filters
          </button>
        </div>
      ) : (
        /* Compact Computer Rows for dense lab environments */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filteredComputers.map((comp, idx) => {
            return (
              <div
                key={comp.terminal_id}
                onClick={() => onSelectComputer && onSelectComputer(comp)}
                className="ios-press"
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-md)',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  boxShadow: 'var(--ios-shadow-subtle, var(--shadow-sm))',
                  cursor: 'pointer',
                  transition: 'transform var(--ios-duration-fast, 0.18s) var(--ios-ease), box-shadow var(--ios-duration-fast, 0.18s) var(--ios-ease), border-color var(--ios-duration-fast, 0.18s) var(--ios-ease)',
                  animation: 'iosFadeInUp var(--ios-duration-normal, 0.26s) var(--ios-spring-soft, cubic-bezier(0.16, 1, 0.3, 1)) both',
                  animationDelay: `${Math.min(idx * 30, 300)}ms`,
                  flexWrap: 'wrap',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.boxShadow = 'var(--ios-shadow-card, 0 4px 12px rgba(0,0,0,0.06))';
                  e.currentTarget.style.transform = 'translateX(4px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-light)';
                  e.currentTarget.style.boxShadow = 'var(--ios-shadow-subtle, var(--shadow-sm))';
                  e.currentTarget.style.transform = 'translateX(0)';
                }}
              >
                {/* Computer Identifier & Online Status */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    minWidth: '220px',
                    flex: '1 1 220px',
                  }}
                >
                  <div
                    style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-secondary)',
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '14px',
                          fontWeight: 700,
                          color: 'var(--text-primary)',
                          letterSpacing: '-0.2px',
                        }}
                      >
                        {comp.hostname || comp.computer_name || comp.terminal_id}
                      </span>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          fontWeight: 600,
                          color: 'var(--text-tertiary)',
                          background: 'var(--bg-secondary)',
                          padding: '1px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        {comp.terminal_id}
                      </span>
                    </div>
                    <div style={{ marginTop: '2px' }}>
                      {getStatusBadge(comp.status)}
                    </div>
                  </div>
                </div>

                {/* Field 1: IP Address */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    minWidth: '130px',
                    flex: '1 1 130px',
                  }}
                >
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: 'var(--text-tertiary)',
                      letterSpacing: '0.4px',
                      marginBottom: '2px',
                    }}
                  >
                    IP Address
                  </span>
                  <div>{renderValue(comp.ip_address, true)}</div>
                </div>

                {/* Field 2: Logged-in User */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    minWidth: '130px',
                    flex: '1 1 130px',
                  }}
                >
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: 'var(--text-tertiary)',
                      letterSpacing: '0.4px',
                      marginBottom: '2px',
                    }}
                  >
                    Logged-in User
                  </span>
                  <div>{renderValue(comp.logged_in_user)}</div>
                </div>

                {/* Field 3: Timestamp (Last Seen) */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    minWidth: '160px',
                    flex: '1 1 160px',
                  }}
                >
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: 'var(--text-tertiary)',
                      letterSpacing: '0.4px',
                      marginBottom: '2px',
                    }}
                  >
                    Timestamp
                  </span>
                  <div>{renderValue(comp.last_seen_formatted, true)}</div>
                </div>

                {/* Action arrow */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingLeft: '8px',
                    color: 'var(--accent)',
                    flexShrink: 0,
                  }}
                >
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-secondary)',
                    }}
                  >
                    <span>View</span>
                    <span>→</span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
