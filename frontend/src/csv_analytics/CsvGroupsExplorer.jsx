import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../useAuthSentinel';
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
  }, [fetchGroups, selectedDimension]);

  const filteredGroups = groups.filter((g) =>
    (g.group_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
      <div className="data-table-container">
        <table className="data-table">
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
              filteredGroups.map((grp, idx) => {
                const normalizedRisk = grp.risk_level === 'NORMAL' ? 'LOW' : (grp.risk_level || 'LOW');
                return (
                  <tr
                    key={grp.group_name}
                    style={{
                      animation: 'iosFadeInUp var(--ios-duration-smooth) var(--ios-ease) both',
                      animationDelay: `${Math.min(idx * 25, 250)}ms`,
                    }}
                  >
                    <td style={{ fontWeight: 600, fontFamily: selectedDimension === 'ip' ? 'var(--font-mono)' : 'inherit' }}>
                      {grp.group_name}
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
                    <td>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ padding: '4px 12px', fontSize: '12px' }}
                        onClick={() => setSelectedGroup(grp)}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
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
