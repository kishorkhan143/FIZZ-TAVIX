import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { BACKEND_URL, parseUtc } from '../useAuthSentinel';
import { springs } from '../motion';
import CustomSelect from '../components/CustomSelect';
import CsvGroupDetailsModal from './CsvGroupDetailsModal';

const DIMENSIONS = [
  { id: 'user', label: 'User' },
  { id: 'ip', label: 'IP Address' },
  { id: 'event_type', label: 'Event Type' },
  { id: 'status', label: 'Status' },
  { id: 'date', label: 'Date' },
  { id: 'hour', label: 'Hour' },
  { id: 'severity', label: 'Severity' },
];

export default function CsvGroupsExplorer({ importId }) {
  const [selectedDimension, setSelectedDimension] = useState('user');
  const [groups, setGroups] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [expandedGroupName, setExpandedGroupName] = useState(null);
  const [groupRecords, setGroupRecords] = useState({});
  const [loadingRecords, setLoadingRecords] = useState(false);

  const fetchGroups = useCallback(async (dimension) => {
    setIsLoading(true);
    try {
      const url = importId
        ? `${BACKEND_URL}/api/csv/groups?import_id=${importId}&group_by=${dimension}`
        : `${BACKEND_URL}/api/csv/groups?group_by=${dimension}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setGroups(data.groups || []);
      }
    } catch (err) {
      console.warn('Failed to fetch groups:', err);
    } finally {
      setIsLoading(false);
    }
  }, [importId]);

  useEffect(() => {
    fetchGroups(selectedDimension);
    setExpandedGroupName(null);
  }, [fetchGroups, selectedDimension]);

  const handleRowClick = async (grp) => {
    if (expandedGroupName === grp.group_name) {
      setExpandedGroupName(null);
      return;
    }
    setExpandedGroupName(grp.group_name);
    if (!groupRecords[grp.group_name]) {
      setLoadingRecords(true);
      try {
        let url = `${BACKEND_URL}/api/csv/records?search=${encodeURIComponent(grp.group_name)}&limit=5`;
        if (importId) url += `&import_id=${importId}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setGroupRecords((prev) => ({ ...prev, [grp.group_name]: data.records || [] }));
        }
      } catch (e) {
        console.warn('Failed to load group history:', e);
      } finally {
        setLoadingRecords(false);
      }
    }
  };

  const fmtTime = (ts) => {
    if (!ts) return '—';
    try {
      return parseUtc(ts).toLocaleTimeString('en-GB', { hour12: false });
    } catch {
      return ts;
    }
  };

  const filteredGroups = groups.filter((g) =>
    (g.group_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="csv-groups-explorer">
      {/* Control Toolbar */}
      <div className="grouping-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
            Group By:
          </span>
          <CustomSelect
            value={selectedDimension}
            onChange={(e) => setSelectedDimension(e.target.value)}
            options={DIMENSIONS.map((d) => ({
              value: d.id,
              label: d.label,
            }))}
            style={{ minWidth: '140px' }}
          />

          <span style={{ fontSize: '12.5px', color: 'var(--text-tertiary)', marginLeft: '6px' }}>
            ({groups.length} distinct groups detected)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ position: 'absolute', left: '10px', color: 'var(--text-tertiary)', pointerEvents: 'none' }}
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="Search group..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                padding: '8px 12px 8px 32px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '12.5px',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                width: '200px',
                outline: 'none',
                transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
              }}
              onFocus={(e) => {
                e.target.style.borderColor = 'var(--accent)';
                e.target.style.boxShadow = '0 0 0 2px rgba(0, 102, 255, 0.12)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = 'var(--border-light)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>
        </div>
      </div>

      {/* Group Table */}
      <div className="csv-groups-table-container">
        <table className="csv-groups-table data-table">
          <thead>
            <tr>
              <th>{selectedDimension === 'user' ? 'User' : (DIMENSIONS.find((d) => d.id === selectedDimension)?.label || 'User')}</th>
              <th>Failed Events</th>
              <th>Successful</th>
              <th>Risk Level</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)' }}>
                  Aggregating records by {selectedDimension}...
                </td>
              </tr>
            ) : filteredGroups.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-tertiary)' }}>
                  No groups match criteria
                </td>
              </tr>
            ) : (
              filteredGroups.map((grp) => {
                const normalizedRisk = grp.risk_level === 'NORMAL' ? 'LOW' : (grp.risk_level || 'LOW');
                const isExpanded = expandedGroupName === grp.group_name;
                const totalEvents = (grp.failed_events || 0) + (grp.successful_events || 0) || 1;
                const failPct = Math.round(((grp.failed_events || 0) / totalEvents) * 100);
                const succPct = Math.round(((grp.successful_events || 0) / totalEvents) * 100);
                const records = groupRecords[grp.group_name] || [];

                return (
                  <tbody key={grp.group_name} style={{ display: 'contents' }}>
                    <tr
                      role="button"
                      tabIndex={0}
                      aria-expanded={isExpanded}
                      onClick={() => handleRowClick(grp)}
                      className={`ios-expandable-row ${isExpanded ? 'is-expanded' : ''}`}
                      style={{
                        cursor: 'pointer',
                        backgroundColor: isExpanded ? 'rgba(0, 102, 255, 0.055)' : undefined,
                        boxShadow: isExpanded ? 'inset 3px 0 0 var(--accent)' : undefined,
                      }}
                      title={`Click to ${isExpanded ? 'collapse' : 'expand'} ${grp.group_name} analytics`}
                    >
                      <td style={{ fontWeight: 600, fontFamily: selectedDimension === 'ip' ? 'var(--font-mono)' : 'inherit' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s ease', color: 'var(--accent)', fontSize: '11px', display: 'inline-block' }}>
                            ▶
                          </span>
                          <span style={{ color: isExpanded ? 'var(--accent)' : 'inherit' }}>{grp.group_name}</span>
                        </div>
                      </td>
                      <td style={{ color: grp.failed_events > 0 ? '#ef4444' : 'inherit', fontWeight: grp.failed_events > 0 ? 600 : 400 }}>
                        {grp.failed_events}
                      </td>
                      <td style={{ color: '#10b981', fontWeight: grp.successful_events > 0 ? 500 : 400 }}>
                        {grp.successful_events}
                      </td>
                      <td>
                        <span className={`severity-pill ${normalizedRisk}`}>
                          {normalizedRisk}
                        </span>
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            style={{ padding: '4px 10px', fontSize: '12px' }}
                            onClick={() => setSelectedGroup(grp)}
                          >
                            Modal Dossier
                          </button>
                          <button
                            type="button"
                            className="ios-collapse-btn"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                            onClick={() => handleRowClick(grp)}
                          >
                            {isExpanded ? '✕ Close' : 'Expand ▾'}
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Smooth Expandable Row Detail Drawer */}
                    {isExpanded && (
                      <tr className="ios-row-detail-container">
                        <td colSpan="5" style={{ padding: 0 }}>
                          <AnimatePresence>
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              transition={springs.soft}
                              className="ios-row-detail-content"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {/* Header */}
                              <div className="ios-expand-header-action">
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span className="ios-expand-title" style={{ fontSize: '14px' }}>
                                    {selectedDimension === 'user' ? 'User Profile & Anomaly Dossier:' : 'Dimension Analysis:'} <strong>{grp.group_name}</strong>
                                  </span>
                                  <span className={`ios-badge-pill ${normalizedRisk.toLowerCase()}`}>
                                    {normalizedRisk} RISK
                                  </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <button
                                    type="button"
                                    className="btn-secondary"
                                    style={{ padding: '3px 10px', fontSize: '11px', borderRadius: '6px' }}
                                    onClick={() => setSelectedGroup(grp)}
                                  >
                                    View Full Dossier Modal ↗
                                  </button>
                                  <button
                                    type="button"
                                    className="ios-collapse-btn"
                                    onClick={() => setExpandedGroupName(null)}
                                  >
                                    ✕ Collapse
                                  </button>
                                </div>
                              </div>

                              {/* Telemetry Breakdown Cards */}
                              <div className="ios-meta-grid">
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Total Correlated Events</span>
                                  <span className="ios-meta-value">{totalEvents}</span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Authentication Failures</span>
                                  <span className="ios-meta-value" style={{ color: grp.failed_events > 0 ? '#ef4444' : 'inherit' }}>
                                    {grp.failed_events || 0} ({failPct}%)
                                  </span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Authorized Successes</span>
                                  <span className="ios-meta-value" style={{ color: '#10b981' }}>
                                    {grp.successful_events || 0} ({succPct}%)
                                  </span>
                                </div>
                                <div className="ios-meta-item">
                                  <span className="ios-meta-label">Risk Band</span>
                                  <span className="ios-meta-value" style={{ color: normalizedRisk === 'CRITICAL' ? '#dc2626' : normalizedRisk === 'HIGH' ? '#ea580c' : '#10b981' }}>
                                    {normalizedRisk}
                                  </span>
                                </div>
                              </div>

                              {/* Ratio Visual Bar */}
                              <div style={{ marginTop: '4px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                                  <span>Success vs Failure Ratio</span>
                                  <span>{succPct}% Success / {failPct}% Failure</span>
                                </div>
                                <div style={{ height: '7px', background: '#fee2e2', borderRadius: '999px', overflow: 'hidden', display: 'flex' }}>
                                  <div style={{ width: `${succPct}%`, background: '#10b981', transition: 'width 0.4s ease' }} />
                                  <div style={{ width: `${failPct}%`, background: '#ef4444', transition: 'width 0.4s ease' }} />
                                </div>
                              </div>

                              {/* Related Event History Section */}
                              <div style={{ marginTop: '10px' }}>
                                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
                                  Recent Correlated Event History
                                </div>
                                {loadingRecords ? (
                                  <div style={{ padding: '12px', fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center' }}>
                                    Loading related audit logs...
                                  </div>
                                ) : records.length === 0 ? (
                                  <div style={{ padding: '8px 12px', fontSize: '12px', color: 'var(--text-tertiary)', background: 'var(--bg-secondary)', borderRadius: '6px' }}>
                                    No granular log lines recorded for this dimension.
                                  </div>
                                ) : (
                                  <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', fontSize: '11.5px', borderCollapse: 'collapse' }}>
                                      <thead>
                                        <tr style={{ borderBottom: '1px solid var(--border-light)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                                          <th style={{ padding: '5px 8px' }}>Time</th>
                                          <th style={{ padding: '5px 8px' }}>Source IP</th>
                                          <th style={{ padding: '5px 8px' }}>Event Type</th>
                                          <th style={{ padding: '5px 8px' }}>Status</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {records.map((r, rIdx) => (
                                          <tr key={r.id || r.row_number || rIdx} style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                                            <td style={{ padding: '5px 8px', fontVariantNumeric: 'tabular-nums' }}>{fmtTime(r.timestamp)}</td>
                                            <td style={{ padding: '5px 8px', fontFamily: 'var(--font-mono)' }}>{r.ip || '—'}</td>
                                            <td style={{ padding: '5px 8px' }}>{r.event_type || 'LOGIN'}</td>
                                            <td style={{ padding: '5px 8px' }}>
                                              <span
                                                style={{
                                                  padding: '2px 7px',
                                                  borderRadius: '4px',
                                                  fontSize: '10.5px',
                                                  fontWeight: 700,
                                                  background: r.status === 'SUCCESS' ? '#ecfdf5' : '#fee2e2',
                                                  color: r.status === 'SUCCESS' ? '#059669' : '#dc2626',
                                                }}
                                              >
                                                {r.status}
                                              </span>
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
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

      {/* Group Details Modal */}
      {selectedGroup && (
        <CsvGroupDetailsModal
          group={selectedGroup}
          dimension={selectedDimension}
          importId={importId}
          onClose={() => setSelectedGroup(null)}
        />
      )}
    </div>
  );
}
