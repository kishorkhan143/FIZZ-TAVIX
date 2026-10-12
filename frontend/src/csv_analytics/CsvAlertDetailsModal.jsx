import { useState } from 'react';
import { BACKEND_URL, parseUtc } from '../useAuthSentinel';
import ModalPortal from '../components/ModalPortal';

export default function CsvAlertDetailsModal({ alert, onClose, onStatusUpdated }) {
  const [currentStatus, setCurrentStatus] = useState(alert?.status || 'OPEN');
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateError, setUpdateError] = useState(null);

  if (!alert) return null;

  const handleUpdateStatus = async (newStatus) => {
    setIsUpdating(true);
    setUpdateError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/csv/alerts/${alert.alert_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update alert status');
      setCurrentStatus(newStatus);
      if (onStatusUpdated) onStatusUpdated(alert.alert_id, newStatus);
    } catch (e) {
      setUpdateError(e.message);
    } finally {
      setIsUpdating(false);
    }
  };

  const fmtTime = (ts) => {
    if (!ts) return '—';
    try {
      const d = parseUtc(ts);
      return d.toLocaleString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return ts;
    }
  };

  const formatAlertTitle = (str) => {
    if (!str) return 'Security alert';
    const clean = str.replace(/_/g, ' ').toLowerCase();
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  };

  // Helper to extract at most 3 clean bullets with compound risks merged
  const getFlaggedBullets = () => {
    const rawReasons = Array.isArray(alert.reasons)
      ? alert.reasons
      : Array.isArray(alert.reason)
      ? alert.reason
      : [];

    const user = alert.user || 'user';
    const ip = alert.ip || 'source IP';
    const eventCount = alert.event_count ?? 0;
    const failedCount = alert.failed_count ?? 0;

    // Check for compound security risk lines to merge
    const compoundLines = rawReasons.filter((r) =>
      r.toLowerCase().includes('compound') ||
      (r.toLowerCase().includes('detection rule') &&
        (r.toLowerCase().includes(user.toLowerCase()) || r.toLowerCase().includes(ip.toLowerCase())))
    );

    let mergedCompoundText = null;
    if (compoundLines.length > 0) {
      const countMatch = compoundLines[0].match(/(\d+)\s+detection rule/i);
      const count = countMatch ? countMatch[1] : compoundLines.length;
      mergedCompoundText = `${count} detection rules triggered for both ${user} and ${ip}`;
    }

    const bullets = [];
    const otherReasons = rawReasons.filter((r) => !compoundLines.includes(r));
    for (const r of otherReasons) {
      bullets.push(r);
    }

    if (mergedCompoundText) {
      bullets.push(mergedCompoundText);
    }

    // Default fallbacks if no specific reasons in data
    if (bullets.length === 0) {
      if (failedCount > 0 && eventCount > 0) {
        bullets.push(`${failedCount} of ${eventCount} login attempts failed`);
      }
      if (failedCount > 0) {
        bullets.push('Failure rate is above the normal limit');
      }
      if (user && ip) {
        bullets.push(`Detection rules triggered for both ${user} and ${ip}`);
      }
    }

    const unique = Array.from(new Set(bullets));
    return unique.slice(0, 3);
  };

  const flaggedBullets = getFlaggedBullets();

  // Reusable array of detail rows in required order
  const detailRows = [
    {
      label: 'Targeted user',
      value: alert.user || '—',
    },
    {
      label: 'Source IP',
      value: (
        <span style={{ fontFamily: 'var(--font-mono)' }}>
          {alert.ip || '—'}
        </span>
      ),
    },
    {
      label: 'Events',
      value: (
        <span>
          {alert.event_count ?? 0} total,{' '}
          <span style={{ color: '#dc2626' }}>
            {alert.failed_count ?? 0} failed
          </span>
        </span>
      ),
    },
    {
      label: 'First seen',
      value: fmtTime(alert.first_seen),
    },
    {
      label: 'Last seen',
      value: fmtTime(alert.last_seen),
    },
  ];

  return (
    <ModalPortal>
      <div className="modal-backdrop" onClick={onClose}>
        <div
          className="modal-dialog alert-modal-dialog"
          onClick={(e) => e.stopPropagation()}
          style={{ maxWidth: '560px' }}
        >
          {/* Header */}
          <div className="modal-header alert-modal-header">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div className="alert-modal-title-row">
                <span className={`severity-pill ${alert.severity || 'CRITICAL'}`}>
                  {alert.severity ? alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1).toLowerCase() : 'Critical'}
                </span>
                <h3 className="alert-modal-title">{formatAlertTitle(alert.type || alert.title)}</h3>
              </div>
              <div className="alert-modal-id-line">
                Alert ID: {alert.alert_id}
              </div>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
              ✕
            </button>
          </div>

          {/* Body */}
          <div className="modal-body alert-modal-body">
            {/* Details Table */}
            <div className="alert-details-table">
              {detailRows.map((row, idx) => (
                <div key={idx} className="alert-details-row">
                  <div className="alert-details-label">{row.label}</div>
                  <div className="alert-details-value">{row.value}</div>
                </div>
              ))}
            </div>

            {/* Incident Summary */}
            {alert.message && (
              <div className="alert-incident-summary">
                {alert.message}
              </div>
            )}

            {/* Why this was flagged */}
            {flaggedBullets.length > 0 && (
              <div className="alert-flagged-section">
                <h4 className="alert-flagged-heading">Why this was flagged</h4>
                <ul className="alert-flagged-list">
                  {flaggedBullets.map((bullet, idx) => (
                    <li key={idx}>{bullet}</li>
                  ))}
                </ul>
              </div>
            )}

            {updateError && (
              <div className="alert-modal-error">
                {updateError}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="modal-footer alert-modal-footer">
            <div className="alert-modal-status-group">
              <span className="alert-status-label">Status:</span>
              <span className={`status-pill ${currentStatus}`}>
                {currentStatus ? currentStatus.charAt(0).toUpperCase() + currentStatus.slice(1).toLowerCase() : 'Open'}
              </span>
            </div>

            <div className="alert-modal-actions">
            </div>
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}
