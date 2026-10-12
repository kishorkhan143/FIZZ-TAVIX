import React, { useState, useMemo } from 'react';
import CustomSelect from '../CustomSelect';
import LiveGroupDetailsModal from './LiveGroupDetailsModal';

export default function LiveGroupedDimensionsView({ events, alerts }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [groupBy, setGroupBy] = useState('user');
  const [selectedGroup, setSelectedGroup] = useState(null);

  // ── Calculate dynamic groupings from real telemetry ──────────
  const groupedData = useMemo(() => {
    if (!events || events.length === 0) return [];

    const map = new Map();

    events.forEach((ev) => {
      const user = ev.username || 'UNKNOWN';
      const ip = ev.source_ip || 'Internal';
      let key = '';

      if (groupBy === 'user') {
        key = `${user}|${ip}`;
      } else if (groupBy === 'ip') {
        key = `${ip}|${user}`;
      } else if (groupBy === 'status') {
        key = `${ev.status || 'UNKNOWN'}|${user}`;
      } else {
        key = `${user}|${ip}`;
      }

      if (!map.has(key)) {
        map.set(key, {
          user,
          sourceIp: ip,
          count: 0,
          failedCount: 0,
          successCount: 0,
          events: [],
          status: 'NORMAL',
          riskLevel: 'LOW',
          attackType: 'STANDARD LOGON',
        });
      }

      const item = map.get(key);
      item.count += 1;
      if (ev.status === 'FAILURE') item.failedCount += 1;
      if (ev.status === 'SUCCESS') item.successCount += 1;
      item.events.push(ev);
    });

    // Cross-correlate with alerts for risk level & attack type
    const result = Array.from(map.values()).map((grp) => {
      // Find matching alert for this user/ip
      const matchingAlert = alerts.find(
        (a) =>
          (a.username && a.username.toLowerCase() === grp.user.toLowerCase()) ||
          (a.source_ip && grp.sourceIp !== 'Internal' && a.source_ip === grp.sourceIp)
      );

      let riskLevel = 'LOW';
      let attackType = 'STANDARD LOGON';
      let status = 'OPEN';

      if (matchingAlert) {
        riskLevel = (matchingAlert.risk_level || 'HIGH').toUpperCase();
        attackType = (matchingAlert.alert_type || 'REPEATED FAILURE').replace(/_/g, ' ');
        status = (matchingAlert.status || (matchingAlert.resolved ? 'RESOLVED' : 'OPEN')).toUpperCase();
      } else if (grp.failedCount >= 5) {
        riskLevel = 'CRITICAL';
        attackType = 'BRUTE FORCE ATTACK';
      } else if (grp.failedCount >= 3) {
        riskLevel = 'HIGH';
        attackType = 'HIGH ERROR RATE';
      } else if (grp.failedCount > 0) {
        riskLevel = 'MEDIUM';
        attackType = 'AUTHENTICATION FAILURE';
      }

      return {
        ...grp,
        riskLevel,
        attackType,
        status,
      };
    });

    // Filter by search
    return result.filter((grp) => {
      if (!searchTerm) return true;
      const s = searchTerm.toLowerCase();
      return (
        grp.user.toLowerCase().includes(s) ||
        grp.sourceIp.toLowerCase().includes(s) ||
        grp.attackType.toLowerCase().includes(s) ||
        grp.riskLevel.toLowerCase().includes(s) ||
        grp.status.toLowerCase().includes(s)
      );
    });
  }, [events, alerts, groupBy, searchTerm]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Control Toolbar */}
      <div className="grouping-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <CustomSelect
            label="Group By:"
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value)}
            options={[
              { value: 'user', label: 'User & Source IP' },
              { value: 'ip', label: 'Source IP' },
              { value: 'status', label: 'Status' },
            ]}
            style={{ minWidth: '150px' }}
          />

          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
            ({groupedData.length} distinct groups detected)
          </span>
        </div>

        <div>
          <input
            type="text"
            placeholder="Search grouped events..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '7px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-normal)',
              fontSize: '13px',
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              width: '240px',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Grouped Dimensions Table */}
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Source IP</th>
              <th>Count</th>
              <th>Attack / Alert Type</th>
              <th>Risk Level</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {groupedData.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '36px', color: 'var(--text-tertiary)' }}>
                  No grouped security events available
                </td>
              </tr>
            ) : (
              groupedData.map((grp, index) => (
                <tr
                  key={`${grp.user}-${grp.sourceIp}-${index}`}
                  style={{
                    animation: 'iosFadeInUp var(--ios-duration-smooth) var(--ios-ease) both',
                    animationDelay: `${Math.min(index * 25, 250)}ms`,
                  }}
                >
                  <td style={{ fontWeight: 600 }}>{grp.user}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{grp.sourceIp}</td>
                  <td>
                    <span style={{ fontWeight: 600 }}>{grp.count}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginLeft: '6px' }}>
                      ({grp.failedCount} failed, {grp.successCount} success)
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{grp.attackType}</td>
                  <td>
                    <span className={`severity-pill ${grp.riskLevel}`}>
                      {grp.riskLevel}
                    </span>
                  </td>
                  <td>
                    <span className={`status-pill ${grp.status}`}>
                      {grp.status}
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
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Group Details Modal */}
      {selectedGroup && (
        <LiveGroupDetailsModal
          group={selectedGroup}
          onClose={() => setSelectedGroup(null)}
        />
      )}
    </div>
  );
}
