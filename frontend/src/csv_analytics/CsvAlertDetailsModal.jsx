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

            {/* ML Analysis — only shown when ML contributed to this alert */}
            {(alert.source === 'ML' || alert.source === 'RULE+ML') && (
              <div className="alert-flagged-section" style={{ marginTop: '12px' }}>
                <h4 className="alert-flagged-heading" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '14px' }}>🤖</span> ML Analysis
                  {alert.source === 'RULE+ML' && (
                    <span style={{ fontSize: '11px', fontWeight: 500, color: 'var(--text-tertiary)' }}>(Rule + ML)</span>
                  )}
                </h4>

                <div className="alert-details-table" style={{ marginTop: '8px' }}>
                  {alert.ml_prediction && (
                    <div className="alert-details-row">
                      <div className="alert-details-label">ML Prediction</div>
                      <div className="alert-details-value" style={{ fontWeight: 600 }}>
                        {alert.ml_prediction.replace(/_/g, ' ')}
                      </div>
                    </div>
                  )}
                  {alert.ml_risk != null && (
                    <div className="alert-details-row">
                      <div className="alert-details-label">Risk Score</div>
                      <div className="alert-details-value">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ flex: 1, background: 'var(--bg-tertiary)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
                            <div style={{ width: `${alert.ml_risk}%`, height: '100%', background: alert.ml_risk >= 70 ? '#ef4444' : alert.ml_risk >= 40 ? '#f59e0b' : '#10b981', borderRadius: '4px' }} />
                          </div>
                          <span style={{ fontSize: '12px', fontWeight: 600, color: alert.ml_risk >= 70 ? '#ef4444' : alert.ml_risk >= 40 ? '#f59e0b' : '#10b981', minWidth: '36px' }}>
                            {alert.ml_risk}/100
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  {alert.ml_confidence != null && (
                    <div className="alert-details-row">
                      <div className="alert-details-label">Confidence</div>
                      <div className="alert-details-value">{Math.round(alert.ml_confidence * 100)}%</div>
                    </div>
                  )}
                  {alert.ml_review_label && (
                    <div className="alert-details-row">
                      <div className="alert-details-label">Review Label</div>
                      <div className="alert-details-value">{alert.ml_review_label}</div>
                    </div>
                  )}
                  {alert.suggested_step && (
                    <div className="alert-details-row">
                      <div className="alert-details-label">Suggested Step</div>
                      <div className="alert-details-value" style={{ fontSize: '12.5px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>{alert.suggested_step}</div>
                    </div>
                  )}
                  {alert.first_seen && alert.last_seen && (() => {
                    const t0 = new Date(alert.first_seen);
                    const t1 = new Date(alert.last_seen);
                    const mins = Math.round((t1 - t0) / 60000);
                    return (
                      <div className="alert-details-row">
                        <div className="alert-details-label">Time Span</div>
                        <div className="alert-details-value" style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                          {fmtTime(alert.first_seen)} – {fmtTime(alert.last_seen)}
                          {mins > 0 && <span style={{ marginLeft: '6px', color: 'var(--text-tertiary)' }}>({mins} min)</span>}
                        </div>
                      </div>
                    );
                  })()}
                  {Array.isArray(alert.related_events) && alert.related_events.length > 0 && (
                    <div className="alert-details-row">
                      <div className="alert-details-label">Event IDs</div>
                      <div className="alert-details-value" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', wordBreak: 'break-word' }}>
                        {alert.related_events.slice(0, 20).join(', ')}
                        {alert.related_events.length > 20 && ` … +${alert.related_events.length - 20} more`}
                      </div>
                    </div>
                  )}
                </div>

                {/* Evidence */}
                {alert.evidence && Object.keys(alert.evidence).length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>Evidence</div>
                    <div className="alert-details-table">
                      {Object.entries(alert.evidence).map(([k, v]) => (
                        <div key={k} className="alert-details-row">
                          <div className="alert-details-label" style={{ fontSize: '11px' }}>{k.replace(/_/g, ' ')}</div>
                          <div className="alert-details-value" style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>{String(v)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Class Probabilities */}
                {alert.class_probabilities && Object.keys(alert.class_probabilities).length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>Class Probabilities</div>
                    {Object.entries(alert.class_probabilities)
                      .filter(([, v]) => v > 0.01)
                      .sort(([, a], [, b]) => b - a)
                      .map(([label, prob]) => (
                        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <div style={{ minWidth: '140px', fontSize: '11.5px', color: 'var(--text-secondary)' }}>{label.replace(/_/g, ' ')}</div>
                          <div style={{ flex: 1, background: 'var(--bg-tertiary)', borderRadius: '3px', height: '5px', overflow: 'hidden' }}>
                            <div style={{ width: `${Math.round(prob * 100)}%`, height: '100%', background: 'var(--accent-primary)', borderRadius: '3px' }} />
                          </div>
                          <div style={{ minWidth: '36px', fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'right' }}>{Math.round(prob * 100)}%</div>
                        </div>
                      ))}
                  </div>
                )}

                <div style={{ marginTop: '10px', padding: '8px 12px', background: 'rgba(59,130,246,0.08)', borderRadius: '8px', fontSize: '12px', color: 'var(--text-secondary)', borderLeft: '3px solid var(--accent-primary)' }}>
                  ⚠️ This is for review purposes only. The system does not block accounts or make final determinations.
                </div>
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
