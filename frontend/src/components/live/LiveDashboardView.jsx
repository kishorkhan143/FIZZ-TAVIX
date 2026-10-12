import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatDateTime } from '../../useAuthSentinel';

export default function LiveDashboardView({ stats, events, alerts }) {
  const hasData = events && events.length > 0;

  // ── Calculate dynamic statistics ─────────────────────────────
  const totalEvents = stats?.total_events || events.length || 0;
  const failedEvents = stats?.failed_logins ?? events.filter(e => e.status === 'FAILURE').length;
  const successEvents = stats?.successful_logins ?? events.filter(e => e.status === 'SUCCESS').length;
  const totalAlerts = stats?.active_alerts ?? alerts.filter(a => !a.resolved).length;
  const criticalAlerts = alerts.filter(a => a.risk_level === 'CRITICAL' && !a.resolved).length;
  const highAlerts = alerts.filter(a => a.risk_level === 'HIGH' && !a.resolved).length;
  const activeIncidents = alerts.filter(a => !a.resolved).length;
  const resolvedIncidents = alerts.filter(a => a.resolved).length;

  // ── Timeline chart data ──────────────────────────────────────
  const timelineData = useMemo(() => {
    if (!events.length) return [];
    // Bucket events by minute or slice latest 15 events
    const sorted = [...events].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const buckets = {};
    sorted.forEach((ev) => {
      const timeStr = formatDateTime(ev.timestamp);
      if (!buckets[timeStr]) {
        buckets[timeStr] = { time: timeStr, events: 0, failures: 0, success: 0 };
      }
      buckets[timeStr].events += 1;
      if (ev.status === 'FAILURE') buckets[timeStr].failures += 1;
      if (ev.status === 'SUCCESS') buckets[timeStr].success += 1;
    });
    return Object.values(buckets).slice(-15);
  }, [events]);

  // ── Authentication status chart data ─────────────────────────
  const authStatusData = useMemo(() => {
    return [
      { name: 'Successful', value: successEvents, color: '#10b981' },
      { name: 'Failed', value: failedEvents, color: '#ef4444' },
    ].filter(d => d.value > 0);
  }, [successEvents, failedEvents]);

  // ── Risk distribution data ───────────────────────────────────
  const riskDistData = useMemo(() => {
    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    alerts.forEach((a) => {
      const r = (a.risk_level || 'LOW').toUpperCase();
      if (counts[r] !== undefined) counts[r]++;
      else counts.LOW++;
    });
    return [
      { name: 'CRITICAL', count: counts.CRITICAL, fill: '#ef4444' },
      { name: 'HIGH', count: counts.HIGH, fill: '#f97316' },
      { name: 'MEDIUM', count: counts.MEDIUM, fill: '#eab308' },
      { name: 'LOW', count: counts.LOW, fill: '#10b981' },
    ];
  }, [alerts]);

  // ── Attack types distribution ────────────────────────────────
  const attackTypesData = useMemo(() => {
    const typesMap = {};
    alerts.forEach((a) => {
      const t = (a.alert_type || 'ANOMALY').replace(/_/g, ' ');
      typesMap[t] = (typesMap[t] || 0) + 1;
    });
    return Object.entries(typesMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [alerts]);

  if (!hasData) {
    return (
      <div className="csv-empty-state-card" style={{ margin: '40px 0' }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--text-tertiary)', marginBottom: '16px' }}>
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
        <h3>No telemetry data available</h3>
        <p>Live telemetry is actively awaiting event ingestion from connected Windows Event Collectors.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 8 Telemetry Statistic Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '14px',
        }}
      >
        <div className="stat-card ios-reveal is-visible ios-stagger-1" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Total Events
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>
            {totalEvents.toLocaleString()}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Live security stream
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-2" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Security Alerts
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#f59e0b', marginTop: '4px' }}>
            {totalAlerts}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Active triggered alerts
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-3" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#ef4444', textTransform: 'uppercase' }}>
            Critical Alerts
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#ef4444', marginTop: '4px' }}>
            {criticalAlerts}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            High severity threats
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-4" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#f97316', textTransform: 'uppercase' }}>
            High Risk Alerts
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#f97316', marginTop: '4px' }}>
            {highAlerts}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Elevated risk incidents
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-5" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Failed Auth
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#dc2626', marginTop: '4px' }}>
            {failedEvents.toLocaleString()}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Failed authentications
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-6" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Successful Auth
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#10b981', marginTop: '4px' }}>
            {successEvents.toLocaleString()}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Authorized logins
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-7" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Active Incidents
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#d97706', marginTop: '4px' }}>
            {activeIncidents}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Under investigation
          </div>
        </div>

        <div className="stat-card ios-reveal is-visible ios-stagger-8" style={{ padding: '16px 20px', borderRadius: 'var(--radius-xl)', background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
            Resolved Incidents
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#059669', marginTop: '4px' }}>
            {resolvedIncidents}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Remediated events
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Events Over Time */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Events Over Time</div>
            </div>
          </div>
          <div className="chart-body">
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="liveEventsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="liveFailuresGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-light)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Area type="monotone" dataKey="events" name="Total Events" stroke="#3b82f6" fill="url(#liveEventsGradient)" strokeWidth={2} />
                <Area type="monotone" dataKey="failures" name="Failures" stroke="#ef4444" fill="url(#liveFailuresGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Authentication Status */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Authentication Status</div>
              <div className="chart-subtitle">Successful vs failed event ratio</div>
            </div>
          </div>
          <div className="chart-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {authStatusData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={authStatusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {authStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p style={{ color: 'var(--text-tertiary)', fontSize: '13px' }}>No authentication events recorded</p>
            )}
          </div>
        </div>

        {/* Risk Level Distribution */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Alerts by Risk Level</div>
              <div className="chart-subtitle">Severity classification distribution</div>
            </div>
          </div>
          <div className="chart-body">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={riskDistData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-light)" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" name="Alerts" radius={[4, 4, 0, 0]}>
                  {riskDistData.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Attack Types Distribution */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">Alerts by Attack Type</div>
              <div className="chart-subtitle">Observed threat signatures</div>
            </div>
          </div>
          <div className="chart-body">
            {attackTypesData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={attackTypesData} layout="vertical" margin={{ top: 10, right: 20, left: 40, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-light)" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} width={110} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="count" name="Alerts" fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-tertiary)', fontSize: '13px' }}>
                No threats detected
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
