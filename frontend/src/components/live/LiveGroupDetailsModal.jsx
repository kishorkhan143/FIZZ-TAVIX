import React from 'react';
import { formatDateTime } from '../../useAuthSentinel';
import ModalPortal from '../ModalPortal';

export default function LiveGroupDetailsModal({ group, onClose }) {
  if (!group) return null;

  return (
    <ModalPortal>
      <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className={`severity-pill ${group.riskLevel}`}>{group.riskLevel}</span>
            <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 700 }}>
              Group Details: {group.user || group.sourceIp || 'Entity'}
            </h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Summary Box */}
          <div
            style={{
              padding: '16px 20px',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-light)',
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>TOTAL EVENTS</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)', marginTop: '2px' }}>
                {group.count}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: '#ef4444', fontWeight: 600 }}>FAILED EVENTS</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#ef4444', marginTop: '2px' }}>
                {group.failedCount}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: '#10b981', fontWeight: 600 }}>SUCCESSFUL</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
                {group.successCount}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>STATUS</div>
              <div style={{ marginTop: '4px' }}>
                <span className={`status-pill ${group.status}`}>{group.status}</span>
              </div>
            </div>
          </div>

          {/* Group Information */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px',
              padding: '16px',
              background: 'var(--bg-card)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-light)',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>User Account</div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {group.user || '—'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>Source IP</div>
              <div style={{ fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '2px' }}>
                {group.sourceIp || 'Internal'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>Attack / Alert Type</div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {group.attackType}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>Country / Region</div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {group.country || 'Local Domain'}
              </div>
            </div>
          </div>

          {/* Associated Events List */}
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Associated Telemetry Events ({group.events?.length || 0})
            </div>
            <div className="data-table-container" style={{ maxHeight: '240px', overflowY: 'auto' }}>
              <table className="data-table" style={{ fontSize: '12px' }}>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Status</th>
                    <th>Terminal</th>
                  </tr>
                </thead>
                <tbody>
                  {!group.events || group.events.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center', padding: '16px', color: 'var(--text-tertiary)' }}>
                        No individual events recorded
                      </td>
                    </tr>
                  ) : (
                    group.events.map((ev, idx) => (
                      <tr key={ev.id || idx}>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{formatDateTime(ev.timestamp)}</td>
                        <td>{ev.logon_type_description || `Event ${ev.event_id || ''}`}</td>
                        <td>
                          <span style={{ color: ev.status === 'SUCCESS' ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                            {ev.status}
                          </span>
                        </td>
                        <td>{ev.target_computer || ev.source_host || '—'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="button" className="btn-secondary" onClick={onClose} style={{ fontSize: '12px' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  </ModalPortal>
);
}
