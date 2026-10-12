import React, { useState } from 'react';
import CustomSelect from '../CustomSelect';
import ModalPortal from '../ModalPortal';

export default function AssignLabModal({ terminal, labs, onClose, onAssign }) {
  const [selectedLabId, setSelectedLabId] = useState(terminal?.lab_id || (labs.length > 0 ? labs[0].id : ''));
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!terminal) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedLabId) return;
    setIsSubmitting(true);
    try {
      await onAssign(terminal.terminal_id, selectedLabId);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const labOptions = labs.map((lab) => ({
    value: lab.id,
    label: `${lab.name} (${lab.id})`,
  }));

  return (
    <ModalPortal>
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
        <div className="modal-header">
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
            Assign Terminal to Laboratory
          </h3>
          <button className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ padding: '12px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 600 }}>TERMINAL IDENTIFIER</div>
              <div style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '2px' }}>
                {terminal.terminal_id}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Last User: <strong>{terminal.account || '—'}</strong> • IP: <code>{terminal.source_ip || '—'}</code>
              </div>
            </div>

            {labs.length === 0 ? (
              <div style={{ padding: '12px', background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '6px', color: '#b45309', fontSize: '12px' }}>
                No laboratories exist yet. Please create a laboratory first in the <strong>Laboratories</strong> tab.
              </div>
            ) : (
              <CustomSelect
                label="Select Target Laboratory:"
                value={selectedLabId}
                onChange={(e) => setSelectedLabId(e.target.value)}
                options={labOptions}
                placeholder="Choose a laboratory..."
              />
            )}
          </div>

          <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting || labs.length === 0}
            >
              {isSubmitting ? 'Assigning...' : 'Assign to Lab'}
            </button>
          </div>
        </form>
      </div>
    </div>
  </ModalPortal>
);
}
