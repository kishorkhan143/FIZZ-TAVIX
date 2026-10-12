import React, { useState, useEffect } from 'react';
import ModalPortal from '../ModalPortal';

/**
 * Format timestamp cleanly as "12 Oct 2026, 00:10:59"
 */
function formatAlertTimestamp(ts) {
  if (!ts) return '12 Oct 2026, 00:10:59';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return '12 Oct 2026, 00:10:59';
    const day = d.getDate();
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[d.getMonth()];
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    return `${day} ${month} ${year}, ${hours}:${minutes}:${seconds}`;
  } catch {
    return '12 Oct 2026, 00:10:59';
  }
}

export default function LiveAlertModal({ alert, onClose, onUpdateStatus, onExecuteAction }) {
  const [actionInProgress, setActionInProgress] = useState(null);
  const [confirmingShutdown, setConfirmingShutdown] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!alert) return null;

  const riskLevel = (alert.risk_level || 'HIGH').toUpperCase();

  const alertTitle = alert.alert_type
    ? alert.alert_type.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase())
    : 'Repeated failure';

  const alertId = alert.id
    ? (String(alert.id).startsWith('ALT-') ? alert.id : `ALT-${String(alert.id).padStart(4, '0')}`)
    : 'ALT-0005';

  const timestamp = formatAlertTimestamp(alert.triggered_at || alert.created_at);

  const user = alert.username || alert.user || 'sec_analyst';
  const machine = alert.source_host || alert.target_computer || 'LAPTOP-A';
  const ip = alert.source_ip || alert.ip || '192.168.1.105';
  const failureCount = alert.failed_count || alert.failure_count || alert.event_count || 5;


  const handleAction = async (actionType, note = '') => {
    setActionInProgress(actionType);
    setFeedback(null);
    try {
      if (onExecuteAction) {
        const res = await onExecuteAction(alert.id, actionType, {
          note,
          terminalId: machine,
        });
        setFeedback({
          type: 'success',
          message: res?.message || `Action ${actionType} executed successfully.`,
        });
      } else if (onUpdateStatus) {
        await onUpdateStatus(alert.id, actionType === 'authorize' ? 'AUTHORIZED' : 'RESOLVED');
        setFeedback({
          type: 'success',
          message: `Alert marked as ${actionType === 'authorize' ? 'AUTHORIZED' : 'RESOLVED'}.`,
        });
      }
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Action execution failed.',
      });
    } finally {
      setActionInProgress(null);
      setConfirmingShutdown(false);
    }
  };

  return (
    <ModalPortal>
      {/* Dimmed backdrop with subtle blur */}
      <div
        className="fixed inset-0 z-[9999] bg-slate-900/40 backdrop-blur-[2px] flex items-center justify-center p-4 overflow-y-auto"
        onClick={onClose}
        aria-modal="true"
        role="dialog"
      >
        {/* Compact, clean, professional white card */}
        <div
          className="w-full max-w-[580px] bg-white rounded-xl border border-neutral-200 shadow-xl p-6 text-left my-auto transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-neutral-100">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-50 text-rose-700 border border-rose-200">
                {riskLevel}
              </span>
              <h2 className="text-lg font-bold text-neutral-900">
                {alertTitle}
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-700 p-1 rounded hover:bg-neutral-100 transition-colors cursor-pointer"
              aria-label="Close modal"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Subtitle */}
          <div className="text-xs text-neutral-500 mt-2.5 mb-3 font-mono">
            Alert ID: {alertId} • {timestamp}
          </div>

          {/* Machine information (3-column clean row) */}
          <div className="grid grid-cols-3 gap-4 py-3 border-y border-neutral-100">
            <div>
              <div className="text-[11px] font-medium text-neutral-500 uppercase tracking-wide mb-1">
                User
              </div>
              <div className="text-sm font-semibold text-neutral-900 truncate" title={user}>
                {user}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-medium text-neutral-500 uppercase tracking-wide mb-1">
                Endpoint Machine
              </div>
              <div className="text-sm font-semibold text-blue-600 truncate" title={machine}>
                {machine}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-medium text-neutral-500 uppercase tracking-wide mb-1">
                IP Address
              </div>
              <div className="text-sm font-mono text-neutral-800 truncate" title={ip}>
                {ip}
              </div>
            </div>
          </div>

          {/* Alert description */}
          <div className="py-3 text-xs leading-relaxed text-neutral-600 border-b border-neutral-100">
            {alert.reason || alert.message || (
              `Multiple failed authentication events were observed for the same account/source within the configured detection window. ${failureCount} failures detected in 120 seconds.`
            )}
          </div>

          {/* Detection details (compact vertical list with monochrome icons) */}
          <div className="py-3.5 space-y-2.5 border-b border-neutral-100">
            {/* Finding 1 */}
            <div className="flex items-start gap-2.5 text-xs text-neutral-700 leading-normal">
              <svg className="w-4 h-4 text-neutral-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                <polyline points="17 6 23 6 23 12" />
              </svg>
              <span>{failureCount} anomalous failed logon attempts detected on {machine}</span>
            </div>

            {/* Finding 2 */}
            <div className="flex items-start gap-2.5 text-xs text-neutral-700 leading-normal">
              <svg className="w-4 h-4 text-neutral-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
              <span>Host IP collected: {ip} (Machine: {machine})</span>
            </div>

            {/* Finding 3 */}
            <div className="flex items-start gap-2.5 text-xs text-neutral-700 leading-normal">
              <svg className="w-4 h-4 text-neutral-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>Detection heuristics flagged high-risk authentication behavior for account {user}</span>
            </div>
          </div>

          {/* Feedback message banner if triggered */}
          {feedback && (
            <div
              className={`mt-3 p-2 rounded text-xs border ${
                feedback.type === 'error'
                  ? 'bg-rose-50 border-rose-200 text-rose-800'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-800'
              }`}
            >
              {feedback.message}
            </div>
          )}

          {/* Shutdown confirmation prompt */}
          {confirmingShutdown && (
            <div className="mt-3 p-2.5 bg-rose-50 border border-rose-200 rounded text-xs flex items-center justify-between gap-2 text-rose-800">
              <span>Confirm remote shutdown on <strong>{machine}</strong> ({ip})?</span>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  onClick={() => handleAction('shutdown', `Admin emergency shutdown issued for ${machine}`)}
                  disabled={actionInProgress !== null}
                  className="px-2.5 py-1 bg-rose-600 text-white rounded font-medium hover:bg-rose-700 transition-colors cursor-pointer"
                >
                  {actionInProgress === 'shutdown' ? 'Shutting down...' : 'Confirm'}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmingShutdown(false)}
                  className="px-2 py-1 border border-neutral-300 bg-white text-neutral-700 rounded hover:bg-neutral-50 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Footer - Response Actions */}
          <div className="pt-4 flex items-center justify-end gap-2">
              {/* Shutdown */}
              <button
                type="button"
                disabled={actionInProgress !== null}
                onClick={() => setConfirmingShutdown(true)}
                className="h-8 px-3 rounded border border-rose-200 text-rose-700 hover:bg-rose-50 hover:border-rose-300 text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                title={`Shut down endpoint ${machine}`}
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                  <line x1="12" y1="2" x2="12" y2="12" />
                </svg>
                <span>Shutdown</span>
              </button>

              {/* Lock Screen */}
              <button
                type="button"
                disabled={actionInProgress !== null}
                onClick={() => handleAction('lock_screen', `Admin locked workstation on ${machine}`)}
                className="h-8 px-3 rounded border border-neutral-300 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-400 text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                title={`Lock screen on ${machine}`}
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <span>Lock Screen</span>
              </button>

              {/* Authorize */}
              <button
                type="button"
                disabled={actionInProgress !== null}
                onClick={() => handleAction('authorize', `Admin verified activity — benign`)}
                className="h-8 px-3 rounded border border-blue-200 text-blue-700 hover:bg-blue-50 hover:border-blue-300 text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                title="Authorize activity — mark as benign"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
                <span>Authorize</span>
              </button>
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}
