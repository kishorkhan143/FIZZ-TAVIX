import { useState, useEffect } from 'react';
import { BACKEND_URL, parseUtc } from '../useAuthSentinel';
import ModalPortal from '../components/ModalPortal';

export default function CsvGroupDetailsModal({ group, dimension, importId, onClose }) {
  const [records, setRecords] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!group || !group.group_name) return;
    const fetchGroupRecords = async () => {
      setIsLoading(true);
      try {
        let url = `${BACKEND_URL}/api/csv/records?search=${encodeURIComponent(group.group_name)}&limit=15`;
        if (importId) url += `&import_id=${importId}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setRecords(data.records || []);
        }
      } catch (e) {
        console.warn('Failed to fetch group event records:', e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchGroupRecords();
  }, [group, importId]);

  if (!group) return null;

  const normalizedRisk = group.risk_level === 'NORMAL' ? 'LOW' : (group.risk_level || 'LOW');

  const fmtTime = (ts) => {
    if (!ts) return '—';
    try {
      return parseUtc(ts).toLocaleTimeString('en-GB', { hour12: false });
    } catch {
      return ts;
    }
  };

  return (
    <ModalPortal>
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal-dialog" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className={`severity-pill ${normalizedRisk}`}>{normalizedRisk}</span>
            <h3>Grouped Security Details</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body" style={{ gap: '18px' }}>
          {/* Summary Card */}
          <div
            style={{
              padding: '16px 20px',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600, textTransform: 'uppercase' }}>
                {dimension ? dimension.toUpperCase() : 'USER'} ENTITY
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>
                {group.group_name}
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '4px' }}>
                SECURITY RISK LEVEL
              </div>
              <div>
                <span className={`severity-pill ${normalizedRisk}`}>{normalizedRisk}</span>
              </div>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="detail-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <div className="detail-item">
              <div className="detail-key">Failed Events</div>
              <div className="detail-val" style={{ color: group.failed_events > 0 ? '#ef4444' : 'inherit', fontSize: '16px' }}>
                {group.failed_events}
              </div>
            </div>

            <div className="detail-item">
              <div className="detail-key">Successful Events</div>
              <div className="detail-val" style={{ color: '#10b981', fontSize: '16px' }}>
                {group.successful_events}
              </div>
            </div>

            <div className="detail-item">
              <div className="detail-key">Total Events</div>
              <div className="detail-val" style={{ fontSize: '16px' }}>
                {group.total_events}
              </div>
            </div>
          </div>

          {/* Related Events Table */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Associated Event Logs ({records.length})
            </div>
            <div className="data-table-container" style={{ maxHeight: '220px', overflowY: 'auto' }}>
              <table className="data-table" style={{ fontSize: '12px' }}>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Source IP</th>
                    <th>Event Type</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '16px', color: 'var(--text-tertiary)' }}>
                        Loading event records...
                      </td>
                    </tr>
                  ) : records.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '16px', color: 'var(--text-tertiary)' }}>
                        No records found for this group
                      </td>
                    </tr>
                  ) : (
                    records.map((r) => (
                      <tr key={r.id || r.row_number}>
                        <td>{fmtTime(r.timestamp)}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{r.ip || '—'}</td>
                        <td>{r.event_type || 'LOGIN'}</td>
                        <td>
                          <span
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 700,
                              background: r.status === 'SUCCESS' ? '#ecfdf5' : '#fee2e2',
                              color: r.status === 'SUCCESS' ? '#059669' : '#dc2626',
                            }}
                          >
                            {r.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ justifyContent: 'flex-end' }}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  </ModalPortal>
);
}
