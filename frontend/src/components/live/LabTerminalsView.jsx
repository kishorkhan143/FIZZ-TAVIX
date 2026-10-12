import React, { useState } from 'react';
import AssignLabModal from './AssignLabModal';

export default function LabTerminalsView({ terminals, labs, onAssign }) {
  const [selectedTerminal, setSelectedTerminal] = useState(null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
          Lab Terminals
        </h3>
      </div>

      <div className="data-table-container">
        <table className="data-table">
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

                return (
                  <tr key={term.terminal_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '13px' }}>
                      {term.terminal_id}
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
                    <td>
                      <button
                        type="button"
                        className={isAssigned ? 'btn-secondary' : 'btn-primary'}
                        style={{ padding: '5px 14px', fontSize: '12px', fontWeight: 600 }}
                        onClick={() => setSelectedTerminal(term)}
                      >
                        {isAssigned ? 'Change Lab' : '+ Add to Lab'}
                      </button>
                    </td>
                  </tr>
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
