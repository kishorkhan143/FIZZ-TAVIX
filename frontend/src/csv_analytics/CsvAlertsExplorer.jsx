import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../useAuthSentinel';
import CustomSelect from '../components/CustomSelect';
import CsvAlertDetailsModal from './CsvAlertDetailsModal';

export default function CsvAlertsExplorer({ importId }) {
  const [alerts, setAlerts] = useState([]);
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);

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

      {/* Security Alerts Table: User | Source IP | Count | Attack / Alert Type | Risk Level | Action */}
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
              filteredAlerts.map((al, idx) => (
                <tr
                  key={al.alert_id}
                  style={{
                    animation: 'iosFadeInUp var(--ios-duration-smooth) var(--ios-ease) both',
                    animationDelay: `${Math.min(idx * 25, 250)}ms`,
                  }}
                >
                  <td style={{ fontWeight: 600 }}>{al.user || '—'}</td>
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
                    <span className={`severity-pill ${al.severity}`}>{al.severity}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ padding: '4px 12px', fontSize: '12px' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedAlert(al);
                      }}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))
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
