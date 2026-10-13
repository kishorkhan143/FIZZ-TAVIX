import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { BACKEND_URL, parseUtc } from '../useAuthSentinel';
import { springs } from '../motion';
import CustomSelect from '../components/CustomSelect';
import CsvAlertDetailsModal from './CsvAlertDetailsModal';

export default function CsvAlertsExplorer({ importId }) {
  const [alerts, setAlerts] = useState([]);
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [expandedAlertId, setExpandedAlertId] = useState(null);
  const [updatingAlertId, setUpdatingAlertId] = useState(null);

  const fetchAlerts = useCallback(async () => {
    setIsLoading(true);
    try {
      let url = `${BACKEND_URL}/api/csv/alerts?`;
      if (importId) url += `import_id=${importId}&`;
      if (severityFilter !== 'ALL') url += `severity=${severityFilter}&`;
      if (statusFilter !== 'ALL') url += `status=${statusFilter}&`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (e) {
      console.warn('Failed to fetch alerts:', e);
    } finally {
      setIsLoading(false);
    }
  }, [importId, severityFilter, statusFilter]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleStatusUpdated = (alertId, newStatus) => {
    setAlerts((prev) =>
      prev.map((a) => (a.alert_id === alertId ? { ...a, status: newStatus } : a))
    );
    if (selectedAlert && selectedAlert.alert_id === alertId) {
      setSelectedAlert((prev) => ({ ...prev, status: newStatus }));
    }
  };

  const handleInlineStatusUpdate = async (e, alertId, newStatus) => {
    e.stopPropagation();
    setUpdatingAlertId(alertId);
    try {
      const res = await fetch(`${BACKEND_URL}/api/csv/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        handleStatusUpdated(alertId, newStatus);
      }
    } catch (err) {
      console.warn('Failed to update alert status:', err);
    } finally {
      setUpdatingAlertId(null);
    }
  };

  const fmtTime = (ts) => {
    if (!ts) return '—';
    try {
      const d = parseUtc(ts);
      return d.toLocaleString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return ts;
    }
  };

  // Dynamic filter for immediate reactivity
  const filteredAlerts = alerts.filter((al) => {
    const matchSeverity =
      severityFilter === 'ALL' || (al.severity || '').toUpperCase() === severityFilter.toUpperCase();
    const matchStatus =
      statusFilter === 'ALL' || (al.status || '').toUpperCase() === statusFilter.toUpperCase();
    return matchSeverity && matchStatus;
  });

  return (
    <div className="csv-alerts-explorer">
      {/* Filters Bar */}
      <div className="grouping-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
          {/* Severity Filter Dropdown Form */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              Severity:
            </span>
            <CustomSelect
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              options={[
                { value: 'ALL', label: 'ALL' },
                { value: 'CRITICAL', label: 'CRITICAL' },
                { value: 'HIGH', label: 'HIGH' },
                { value: 'MEDIUM', label: 'MEDIUM' },
                { value: 'LOW', label: 'LOW' },
              ]}
              style={{ minWidth: '120px' }}
            />
          </div>

          {/* Status Filter Dropdown Form */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              Status:
            </span>
            <CustomSelect
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'ALL', label: 'ALL' },
                { value: 'OPEN', label: 'OPEN' },
                { value: 'INVESTIGATING', label: 'INVESTIGATING' },
                { value: 'RESOLVED', label: 'RESOLVED' },
              ]}
              style={{ minWidth: '140px' }}
            />
          </div>
        </div>

        <div style={{ fontSize: '12.5px', fontWeight: 500, color: 'var(--text-tertiary)', background: 'var(--bg-secondary)', padding: '6px 14px', borderRadius: '100px', border: '1px solid var(--border-light)' }}>
          Showing <strong style={{ color: 'var(--text-primary)' }}>{filteredAlerts.length}</strong> alerts
        </div>
      </div>

      {/* Security Alerts Table */}
      <div className="csv-alerts-table-container">
        <table className="csv-alerts-table data-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Source IP</th>
              <th>Count</th>
              <th>Attack / Alert Type</th>
              <th>Risk Level</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)' }}>
                  Loading security alerts...
                </td>
              </tr>
            ) : filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)' }}>
                  No security alerts match the selected filters
                </td>
              </tr>
            ) : (
              filteredAlerts.map((al) => {
                const isExpanded = expandedAlertId === al.alert_id;
                const status = (al.status || 'OPEN').toUpperCase();
                const sev = (al.severity || 'LOW').toUpperCase();

                return (
                  <tbody key={al.alert_id} style={{ display: 'contents' }}>
                    <tr
                      role="button"
                      tabIndex={0}
                      aria-expanded={isExpanded}
                      onClick={() => setExpandedAlertId(isExpanded ? null : al.alert_id)}
                      className={`ios-expandable-row ${isExpanded ? 'is-expanded' : ''}`}
                      style={{
                        cursor: 'pointer',
                        backgroundColor: isExpanded ? 'rgba(0, 102, 255, 0.055)' : undefined,
                        boxShadow: isExpanded ? 'inset 3px 0 0 var(--accent)' : undefined,
                      }}
                      title={`Click to ${isExpanded ? 'collapse' : 'expand'} alert details`}
                    >
                      <td style={{ fontWeight: 600 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s ease', color: 'var(--accent)', fontSize: '11px', display: 'inline-block' }}>
                            ▶
                          </span>
                          <span style={{ color: isExpanded ? 'var(--accent)' : 'inherit' }}>{al.user || '—'}</span>
                        </div>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{al.ip || '—'}</td>
                      <td>
                        {al.event_count}
                        {al.failed_count > 0 && (
                          <span style={{ color: '#ef4444', fontSize: '11px', marginLeft: '4px' }}>
                            ({al.failed_count} failed)
                          </span>
                        )}
                      </td>
                      <td style={{ fontWeight: 600 }}>{(al.type || '').replace(/_/g, ' ')}</td>
                      <td>
                        <span className={`severity-pill ${sev}`}>{sev}</span>
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            style={{ padding: '4px 10px', fontSize: '12px' }}
                            onClick={() => setSelectedAlert(al)}
                          >
                            Modal
                          </button>
                          <button
                            type="button"
                            className="ios-collapse-btn"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                            onClick={() => setExpandedAlertId(isExpanded ? null : al.alert_id)}
                          >
                            {isExpanded ? '✕ Close' : 'Expand ▾'}
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Smooth Expandable Alert Detail Drawer */}
                    {isExpanded && (
                      <tr className="ios-row-detail-container">
                        <td colSpan="6" style={{ padding: 0 }}>
                          <AnimatePresence>
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              transition={springs.soft}
                              className="ios-row-detail-content"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <div className="ios-expand-header-action">
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span className="ios-expand-title" style={{ fontSize: '14px' }}>
                                    Alert Dossier #{al.alert_id} • {(al.type || '').replace(/_/g, ' ')}
                                  </span>
                                  <span className={`ios-badge-pill ${sev.toLowerCase()}`}>
                                    {sev} SEVERITY
                                  </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <button
                                    type="button"
                                    className="btn-secondary"
                                    style={{ padding: '3px 10px', fontSize: '11px', borderRadius: '6px' }}
                                    onClick={() => setSelectedAlert(al)}
                                  >
                                    View Full Dossier Modal ↗
                                  </button>
                                  <button
                                    type="button"
                                    className="ios-collapse-btn"
                                    onClick={() => setExpandedAlertId(null)}
                                  >
                                    ✕ Collapse
                                  </button>
                                </div>
                              </div>

                              <div className="ios-meta-grid">
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Flagged Account</span>
                                  <span className="ios-meta-value">{al.user || 'Unspecified'}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Source IP Address</span>
                                  <span className="ios-meta-value">{al.ip || '—'}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Total Correlated Events</span>
                                  <span className="ios-meta-value">{al.event_count || 0}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Failed Attempts</span>
                                  <span className="ios-meta-value" style={{ color: al.failed_count > 0 ? '#ef4444' : 'inherit' }}>
                                    {al.failed_count || 0} failures
                                  </span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Current Triage State</span>
                                  <span className="ios-meta-value" style={{ color: status === 'RESOLVED' ? '#10b981' : '#f59e0b' }}>
                                    {status}
                                  </span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">First Triggered</span>
                                  <span className="ios-meta-value">{fmtTime(al.first_seen || al.timestamp)}</span>
                                </div>
                              </div>

                              {/* Triage Action Buttons */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px', flexWrap: 'wrap' }}>
                                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Triage Status:</span>
                                {['OPEN', 'INVESTIGATING', 'RESOLVED'].map((st) => (
                                  <button
                                    key={st}
                                    type="button"
                                    disabled={updatingAlertId === al.alert_id || status === st}
                                    onClick={(e) => handleInlineStatusUpdate(e, al.alert_id, st)}
                                    style={{
                                      padding: '3px 10px',
                                      fontSize: '11px',
                                      fontWeight: 600,
                                      borderRadius: '6px',
                                      border: status === st ? '1.5px solid var(--accent)' : '1px solid var(--border-normal)',
                                      background: status === st ? 'rgba(0, 102, 255, 0.08)' : 'var(--bg-secondary)',
                                      color: status === st ? 'var(--accent)' : 'var(--text-primary)',
                                      cursor: status === st ? 'default' : 'pointer',
                                    }}
                                  >
                                    {st === 'RESOLVED' ? '✓ Mark Resolved' : st === 'INVESTIGATING' ? '⚡ Investigating' : 'Open'}
                                  </button>
                                ))}
                              </div>
                            </motion.div>
                          </AnimatePresence>
                        </td>
                      </tr>
                    )}
                  </tbody>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Alert Details Modal */}
      {selectedAlert && (
        <CsvAlertDetailsModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onStatusUpdated={handleStatusUpdated}
        />
      )}
    </div>
  );
}
