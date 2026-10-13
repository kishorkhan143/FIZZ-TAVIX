import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { springs } from '../../motion';
import AssignLabModal from './AssignLabModal';

export default function LabTerminalsView({ terminals, labs, onAssign }) {
  const [selectedTerminal, setSelectedTerminal] = useState(null);
  const [expandedTermId, setExpandedTermId] = useState(null);

  return (
    <div className="lab-terminals-view">
      <div className="lab-terminals-header">
        <h3 className="lab-terminals-heading">
          Lab Terminals
        </h3>
      </div>

      <div className="lab-terminals-table-container">
        <table className="lab-terminals-table data-table">
          <thead>
            <tr>
              <th>Terminal ID</th>
              <th>Account/User</th>
              <th>Source IP</th>
              <th>Last Login</th>
              <th>Login Status</th>
              <th>Lab</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {!terminals || terminals.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '36px', color: 'var(--text-tertiary)' }}>
                  No terminal data available.
                </td>
              </tr>
            ) : (
              terminals.map((term) => {
                const isAssigned = !!term.lab_name || !!term.lab_id;
                const isExpanded = expandedTermId === term.terminal_id;

                return (
                  <tbody key={term.terminal_id} style={{ display: 'contents' }}>
                    <tr
                      role="button"
                      tabIndex={0}
                      aria-expanded={isExpanded}
                      onClick={() => setExpandedTermId(isExpanded ? null : term.terminal_id)}
                      className={`ios-expandable-row ${isExpanded ? 'is-expanded' : ''}`}
                      style={{
                        cursor: 'pointer',
                        backgroundColor: isExpanded ? 'rgba(0, 102, 255, 0.055)' : undefined,
                        boxShadow: isExpanded ? 'inset 3px 0 0 var(--accent)' : undefined,
                      }}
                      title={`Click to ${isExpanded ? 'collapse' : 'expand'} terminal details`}
                    >
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '13px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s ease', color: 'var(--accent)', fontSize: '11px', display: 'inline-block' }}>
                            ▶
                          </span>
                          <span style={{ color: isExpanded ? 'var(--accent)' : 'inherit' }}>{term.terminal_id}</span>
                        </div>
                      </td>
                      <td style={{ fontWeight: 600 }}>{term.account || '—'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                        {term.source_ip || 'Internal'}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {term.last_login || '—'}
                      </td>
                      <td>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            fontWeight: 600,
                            fontSize: '12px',
                            color: term.status === 'SUCCESS' ? '#10b981' : '#ef4444',
                          }}
                        >
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              background: term.status === 'SUCCESS' ? '#10b981' : '#ef4444',
                            }}
                          />
                          {term.status || 'UNKNOWN'}
                        </span>
                      </td>
                      <td>
                        {isAssigned ? (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '3px 10px',
                              borderRadius: '6px',
                              fontSize: '11px',
                              fontWeight: 700,
                              background: '#eff6ff',
                              color: '#2563eb',
                              border: '1px solid #bfdbfe',
                            }}
                          >
                            {term.lab_name || term.lab_id}
                          </span>
                        ) : (
                          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                            Unassigned
                          </span>
                        )}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <button
                            type="button"
                            className={isAssigned ? 'btn-secondary' : 'btn-primary'}
                            style={{ padding: '4px 12px', fontSize: '12px', fontWeight: 600 }}
                            onClick={() => setSelectedTerminal(term)}
                          >
                            {isAssigned ? 'Change Lab' : '+ Assign'}
                          </button>
                          <button
                            type="button"
                            className="ios-collapse-btn"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                            onClick={() => setExpandedTermId(isExpanded ? null : term.terminal_id)}
                          >
                            {isExpanded ? '✕ Close' : 'Expand ▾'}
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Smooth Expandable Row Detail Drawer */}
                    {isExpanded && (
                      <tr className="ios-row-detail-container">
                        <td colSpan="7" style={{ padding: 0 }}>
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
                                    Workstation Dossier: <strong>{term.terminal_id}</strong>
                                  </span>
                                  <span className={`ios-badge-pill ${term.status === 'SUCCESS' ? 'success' : 'failure'}`}>
                                    {term.status === 'SUCCESS' ? 'NORMAL STATUS' : 'FLAGGED LOGIN'}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <button
                                    type="button"
                                    className="btn-secondary"
                                    style={{ padding: '3px 10px', fontSize: '11px', borderRadius: '6px' }}
                                    onClick={() => setSelectedTerminal(term)}
                                  >
                                    Assign / Manage Lab ↗
                                  </button>
                                  <button
                                    type="button"
                                    className="ios-collapse-btn"
                                    onClick={() => setExpandedTermId(null)}
                                  >
                                    ✕ Collapse
                                  </button>
                                </div>
                              </div>

                              <div className="ios-meta-grid">
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Active User Session</span>
                                  <span className="ios-meta-value">{term.account || 'None (Idle)'}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Assigned Laboratory</span>
                                  <span className="ios-meta-value">{term.lab_name || term.lab_id || 'Unassigned'}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Network IPv4 Address</span>
                                  <span className="ios-meta-value">{term.source_ip || '127.0.0.1'}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Last Logon Recorded</span>
                                  <span className="ios-meta-value">{term.last_login || '—'}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Authentication Outcome</span>
                                  <span className="ios-meta-value" style={{ color: term.status === 'SUCCESS' ? '#10b981' : '#ef4444' }}>
                                    {term.status || 'UNKNOWN'}
                                  </span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Defense State</span>
                                  <span className="ios-meta-value" style={{ color: '#10b981' }}>Active Surveillance</span>
                                </div>
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

      {/* Assign Modal */}
      {selectedTerminal && (
        <AssignLabModal
          terminal={selectedTerminal}
          labs={labs}
          onClose={() => setSelectedTerminal(null)}
          onAssign={onAssign}
        />
      )}
    </div>
  );
}
