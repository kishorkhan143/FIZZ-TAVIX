import React, { useState } from 'react';
import ModalPortal from '../ModalPortal';

export default function AddLabModal({ onClose, onAddLab }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [labId, setLabId] = useState(`LAB-${Math.floor(100 + Math.random() * 900)}`);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a laboratory name.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await onAddLab({
        id: labId.trim() || undefined,
        name: name.trim(),
        description: description.trim() || undefined,
        location: location.trim() || undefined,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create laboratory.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ModalPortal>
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 700 }}>Add New Laboratory</h3>
          <button className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {error && (
              <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#b91c1c', fontSize: '13px' }}>
                {error}
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Lab ID (Auto-generated)
              </label>
              <input
                type="text"
                value={labId}
                onChange={(e) => setLabId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-normal)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                  fontFamily: 'var(--font-mono)',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Laboratory Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Cyber Security Lab A"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-normal)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Location / Facility
              </label>
              <input
                type="text"
                placeholder="e.g. Building 4, Room 202"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-normal)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Description
              </label>
              <textarea
                placeholder="Description of the test environment and research scope..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-normal)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                  resize: 'vertical',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>

          <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Lab'}
            </button>
          </div>
        </form>
      </div>
    </div>
  </ModalPortal>
);
}
