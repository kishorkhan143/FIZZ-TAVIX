import React, { useState, useEffect } from "react";
import ModalPortal from "../ModalPortal";
import "./LiveAlertModal.css";

/**
 * Format timestamp cleanly as "12 Oct 2026, 00:10:59"
 */
function formatAlertTimestamp(ts) {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "—";
    const day = d.getDate();
    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const month = months[d.getMonth()];
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");
    return `${day} ${month} ${year}, ${hours}:${minutes}:${seconds}`;
  } catch {
    return "—";
  }
}

export default function LiveAlertModal({ alert, onClose, onUpdateStatus, onExecuteAction }) {
  const [actionInProgress, setActionInProgress] = useState(null);
  const [confirmingShutdown, setConfirmingShutdown] = useState(false);
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && onClose) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!alert) return null;

  const riskLevel = (alert.risk_level || "UNKNOWN").toUpperCase();
  const alertTitle = alert.alert_type
    ? alert.alert_type
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/^\w/, (c) => c.toUpperCase())
    : "Security incident";
  const alertId = alert.id
    ? String(alert.id).startsWith("ALT-")
      ? alert.id
      : `ALT-${String(alert.id).padStart(4, "0")}`
    : "—";
  const timestamp = formatAlertTimestamp(alert.triggered_at || alert.created_at);
  const user = alert.username || alert.user || "—";
  const candidateMachine = alert.source_host || alert.target_computer;
  const machine = candidateMachine && !["UNKNOWN", "—", "-"].includes(String(candidateMachine).trim().toUpperCase())
    ? String(candidateMachine).trim()
    : "";
  const ip = alert.source_ip || alert.ip || "—";
  const hasRemoteTarget = Boolean(machine || (ip !== "—" && ip !== "UNKNOWN"));
  const targetLabel = machine || ip;
  const failureCount = alert.failed_count ?? alert.failure_count ?? alert.event_count;
  const status = String(alert.status || (alert.resolved ? "RESOLVED" : "OPEN"))
    .toUpperCase()
    .replace(/_/g, " ");

  const handleAction = async (actionType, note = "") => {
    setActionInProgress(actionType);
    setActionError("");
    try {
      if (onExecuteAction) {
        await onExecuteAction(alert.id, actionType, {
          note,
          terminalId: machine || undefined,
        });
      } else if (onUpdateStatus) {
        await onUpdateStatus(
          alert.id,
          actionType === "authorize" ? "AUTHORIZED" : "RESOLVED"
        );
      } else {
        throw new Error("Alert action handler is unavailable.");
      }
      // Close modal after action
      setTimeout(() => onClose(), 300);
    } catch (err) {
      console.error("Action failed:", err);
      setActionError(err instanceof Error ? err.message : "Alert action failed.");
    } finally {
      setActionInProgress(null);
      setConfirmingShutdown(false);
    }
  };

  return (
    <ModalPortal>
      <div
        className="live-alert-backdrop"
        onClick={onClose}
        aria-modal="true"
        role="dialog"
        aria-labelledby="live-alert-title"
      >
        <div
          className="live-alert-dialog"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="live-alert-header">
            <div className="live-alert-heading">
              <span className="live-alert-severity">
                {riskLevel}
              </span>
              <div className="live-alert-title-block">
                <h2 id="live-alert-title" className="live-alert-title">
                  {alertTitle}
                </h2>
                <p className="live-alert-meta">
                  Alert ID: {alertId} <span aria-hidden="true">•</span> {timestamp}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="live-alert-close"
              aria-label="Close"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </header>

          <section className="live-alert-info" aria-label="Alert target">
            <div className="live-alert-info-item">
              <p className="live-alert-label">Targeted user</p>
              <p className="live-alert-value">{user}</p>
            </div>
            <div className="live-alert-info-item">
              <p className="live-alert-label">Endpoint Machine</p>
              <p className="live-alert-value live-alert-machine">{machine || "—"}</p>
            </div>
            <div className="live-alert-info-item">
              <p className="live-alert-label">IP Address</p>
              <p className="live-alert-value live-alert-ip">{ip}</p>
            </div>
          </section>

          <div className="live-alert-summary">
            <p>
              {alert.reason ||
                alert.message ||
                "No additional incident details were provided."}
            </p>
          </div>

          <section className="live-alert-details">
            <h3>Details</h3>
            <div className="live-alert-findings">
              <div className="live-alert-finding">
                <span className="live-alert-finding-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                    <polyline points="17 6 23 6 23 12" />
                  </svg>
                </span>
                <p>
                  {failureCount !== undefined && failureCount !== null
                    ? `${failureCount} failed logon attempts recorded`
                    : "Failure count unavailable"}
                  {machine ? ` on ${machine}` : ""}
                </p>
              </div>
              <div className="live-alert-finding">
                <span className="live-alert-finding-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                </span>
                <p>Host IP: {ip}{machine ? ` (Machine: ${machine})` : ""}</p>
              </div>
              <div className="live-alert-finding">
                <span className="live-alert-finding-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                </span>
                <p>
                  {alert.reason || alert.message
                    ? "Detection details are provided above."
                    : "Additional detection details are unavailable."}
                </p>
              </div>
            </div>
          </section>

          <footer className="live-alert-footer">
            <div className="live-alert-status">
              <span>Current Status</span>
              <strong>{status}</strong>
            </div>
            <div className="live-alert-actions">
              <button
                type="button"
                onClick={() => setConfirmingShutdown(true)}
                disabled={Boolean(actionInProgress) || !hasRemoteTarget}
                className="live-alert-action live-alert-action-shutdown"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                  <line x1="12" y1="2" x2="12" y2="12" />
                </svg>
                Shutdown
              </button>
              <button
                type="button"
                onClick={() => handleAction("lock_screen", `Admin locked ${targetLabel}`)}
                disabled={Boolean(actionInProgress) || !hasRemoteTarget}
                className="live-alert-action live-alert-action-lock"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                Lock
              </button>
              <button
                type="button"
                onClick={() => handleAction("authorize", "Admin verified")}
                disabled={Boolean(actionInProgress)}
                className="live-alert-action live-alert-action-authorize"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
                Authorize
              </button>
            </div>
          </footer>

          {confirmingShutdown && (
            <div className="live-alert-confirm">
              <p>
                Confirm remote shutdown on <strong>{targetLabel}</strong>
                {machine && ip !== "—" ? ` (${ip})` : ""}?
              </p>
              <div className="live-alert-confirm-actions">
                <button
                  type="button"
                  onClick={() => handleAction("shutdown", `Admin shutdown on ${targetLabel}`)}
                  disabled={Boolean(actionInProgress) || !hasRemoteTarget}
                >
                  {actionInProgress === "shutdown" ? "..." : "Confirm"}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmingShutdown(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
          {actionError && (
            <p role="alert" style={{ color: "#dc2626", padding: "0 32px 18px" }}>
              {actionError}
            </p>
          )}
        </div>
      </div>
    </ModalPortal>
  );
}
