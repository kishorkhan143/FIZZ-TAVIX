import React, { useState, useEffect } from 'react';
import AddLabModal from './AddLabModal';
import { formatDateTime } from '../../useAuthSentinel';

export default function LaboratoriesView({
  labs = [],
  onAddLab,
  onDeleteLab,
  onSelectLab,
  labHours,
  onUpdateLabHours,
}) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [startTime, setStartTime] = useState(labHours?.start_time || '09:00');
  const [endTime, setEndTime] = useState(labHours?.end_time || '18:00');
  const [savedToast, setSavedToast] = useState(false);
  const [hoursSaveError, setHoursSaveError] = useState('');
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    if (labHours?.start_time) setStartTime(labHours.start_time);
    if (labHours?.end_time) setEndTime(labHours.end_time);
  }, [labHours]);

  // Keep live time ticking every 30s to update inside/outside status
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 30000);
    return () => clearInterval(timer);
  }, []);

  const calculateWithinHours = (st, et) => {
    try {
      const [sh, sm] = (st || '09:00').split(':').map(Number);
      const [eh, em] = (et || '18:00').split(':').map(Number);
      const cur = currentTime.getHours() * 60 + currentTime.getMinutes();
      const startMin = sh * 60 + sm;
      const endMin = eh * 60 + em;
      if (startMin <= endMin) {
        return cur >= startMin && cur < endMin;
      }
      return cur >= startMin || cur < endMin;
    } catch {
      return true;
    }
  };

  const isWithinHours = calculateWithinHours(startTime, endTime);

  const handleStartTimeChange = async (e) => {
    const newStart = e.target.value;
    setStartTime(newStart);
    setSavedToast(false);
    setHoursSaveError('');
    if (onUpdateLabHours && newStart && endTime) {
      try {
        await onUpdateLabHours(newStart, endTime);
        setSavedToast(true);
        setTimeout(() => setSavedToast(false), 2000);
      } catch (err) {
        setStartTime(startTime);
        setHoursSaveError(err instanceof Error ? err.message : 'Failed to save lab hours.');
      }
    }
  };

  const handleEndTimeChange = async (e) => {
    const newEnd = e.target.value;
    setEndTime(newEnd);
    setSavedToast(false);
    setHoursSaveError('');
    if (onUpdateLabHours && startTime && newEnd) {
      try {
        await onUpdateLabHours(startTime, newEnd);
        setSavedToast(true);
        setTimeout(() => setSavedToast(false), 2000);
      } catch (err) {
        setEndTime(endTime);
        setHoursSaveError(err instanceof Error ? err.message : 'Failed to save lab hours.');
      }
    }
  };

  return (
    <div className="section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top action bar with Lab Time controls and Add Lab button */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          paddingBottom: '12px',
          borderBottom: '1px solid var(--border-light)',
        }}
      >
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            Laboratories
          </h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Lab Operating Hours Selector (Near Add Lab) */}
          <div
            className="lab-time-bar"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '12px',
              padding: '6px 14px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-normal)',
              borderRadius: 'var(--radius-md, 8px)',
              boxShadow: 'var(--ios-shadow-subtle, 0 1px 3px rgba(0,0,0,0.05))',
              whiteSpace: 'nowrap',
            }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ color: 'var(--accent)' }}>
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Lab Time:
              </span>
            </div>

            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>From</span>
              <input
                type="time"
                id="input-labtime-from"
                value={startTime}
                onChange={handleStartTimeChange}
                className="lab-time-input"
                title="Start of authorized lab hours"
                style={{
                  height: '28px',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-normal)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  outline: 'none',
                }}
              />
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>To</span>
              <input
                type="time"
                id="input-labtime-to"
                value={endTime}
                onChange={handleEndTimeChange}
                className="lab-time-input"
                title="End of authorized lab hours"
                style={{
                  height: '28px',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-normal)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  outline: 'none',
                }}
              />
            </div>

            {savedToast && (
              <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 600, marginLeft: '2px' }}>
                ✓ Saved
              </span>
            )}
            {hoursSaveError && (
              <span role="alert" style={{ fontSize: '11px', color: '#dc2626', fontWeight: 600, marginLeft: '2px' }}>
                {hoursSaveError}
              </span>
            )}
          </div>

          {/* Add Lab Button (Single + Icon) */}
          <button
            type="button"
            id="btn-add-lab-top"
            className="btn-primary"
            onClick={() => setShowAddModal(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 18px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent)',
              color: '#ffffff',
              border: 'none',
              boxShadow: '0 2px 6px rgba(0, 102, 255, 0.25)',
              transition: 'all 0.2s ease',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>Add Lab</span>
          </button>
        </div>
      </div>

      {/* Labs List / Grid */}
      {(!labs || labs.length === 0) ? (
        <div
          className="empty-state"
          style={{
            padding: '60px 24px',
            textAlign: 'center',
            background: 'var(--bg-secondary)',
            border: '1px dashed var(--border-normal)',
            borderRadius: 'var(--radius-xl)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '20px 0',
          }}
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--text-tertiary)', marginBottom: '16px' }}>
            <path d="M4.54 11.46L2.19 14.81A2 2 0 0 0 3.81 18h16.38a2 2 0 0 0 1.62-3.19l-2.35-3.35" />
            <path d="M6 4h12v7H6z" />
          </svg>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 8px 0' }}>No laboratories configured</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', maxWidth: '420px', margin: '0 0 20px 0' }}>
            Click the <strong>Add Lab</strong> button above to register and configure your first test environment.
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setShowAddModal(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 18px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent)',
              color: '#ffffff',
              border: 'none',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>Add Lab Now</span>
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '14px' }}>
          {labs.map((lab, idx) => (
            <div
              key={lab.id}
              id={`lab-card-${lab.id}`}
              onClick={() => onSelectLab && onSelectLab(lab)}
              className="lab-card"
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-lg, 14px)',
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: 'var(--ios-shadow-subtle, var(--shadow-sm))',
                cursor: 'pointer',
                transition: 'transform var(--ios-duration-normal, 0.26s) var(--ios-spring-soft, cubic-bezier(0.16, 1, 0.3, 1)), box-shadow var(--ios-duration-normal, 0.26s) var(--ios-ease), border-color var(--ios-duration-normal, 0.26s) var(--ios-ease)',
                animation: 'iosFadeInUp var(--ios-duration-smooth, 0.34s) var(--ios-spring-soft, cubic-bezier(0.16, 1, 0.3, 1)) both',
                animationDelay: `${idx * 40}ms`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.boxShadow = 'var(--ios-shadow-card-hover)';
                e.currentTarget.style.transform = 'translateY(-3px) scale(1.01)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-light)';
                e.currentTarget.style.boxShadow = 'var(--ios-shadow-subtle, var(--shadow-sm))';
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '10.5px',
                      fontWeight: 700,
                      background: 'var(--accent-light)',
                      color: 'var(--accent)',
                      padding: '2px 7px',
                      borderRadius: '5px',
                    }}
                  >
                    {lab.id}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteLab(lab.id);
                    }}
                    title="Delete Laboratory"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-tertiary)',
                      cursor: 'pointer',
                      fontSize: '12px',
                      padding: '2px 4px',
                      lineHeight: 1,
                    }}
                  >
                    ✕
                  </button>
                </div>

                <h4 style={{ fontSize: '14.5px', fontWeight: 700, margin: '0 0 4px 0', color: 'var(--text-primary)' }}>
                  {lab.name}
                </h4>

                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '0 0 8px 0', lineHeight: 1.35 }}>
                  {lab.description || 'No description provided.'}
                </p>

                {lab.location && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11.5px', color: 'var(--text-tertiary)', marginBottom: '6px' }}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                    <span>{lab.location}</span>
                  </div>
                )}

                {/* Lab Hours info on card */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    fontSize: '11px',
                    color: 'var(--text-secondary)',
                    marginTop: '4px',
                    padding: '3px 6px',
                    background: 'var(--bg-secondary)',
                    borderRadius: '5px',
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--text-tertiary)' }}>
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span>Hours: <strong>{startTime} - {endTime}</strong></span>
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '10px',
                  paddingTop: '8px',
                  borderTop: '1px solid var(--border-light)',
                  fontSize: '11.5px',
                  color: 'var(--accent)',
                  fontWeight: 600,
                }}
              >
                <span>View connected computers</span>
                <span>→</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Lab Modal */}
      {showAddModal && (
        <AddLabModal
          onClose={() => setShowAddModal(false)}
          onAddLab={onAddLab}
        />
      )}
    </div>
  );
}
