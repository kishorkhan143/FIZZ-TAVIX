import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { springs } from '../motion';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

export default function CsvAnalyticsCharts({ summary }) {
  const [expandedChart, setExpandedChart] = useState(null);

  if (!summary || !summary.analysis_summary) return null;

  const analysis = summary.analysis_summary;

  // 1. Successful vs Failed Events
  const successCount = analysis.success_count || 0;
  const failureCount = analysis.failure_count || 0;
  const totalEvents = successCount + failureCount || 1;
  const successPct = Math.round((successCount / totalEvents) * 100);
  const failurePct = Math.round((failureCount / totalEvents) * 100);

  const outcomeData = [
    { name: 'Successful', value: successCount, color: '#10b981' },
    { name: 'Failed', value: failureCount, color: '#ef4444' },
  ].filter((d) => d.value > 0);

  // 2. Risk Level Distribution (LOW, MEDIUM, HIGH, CRITICAL)
  const riskDist = analysis.risk_band_distribution || {};
  const lowCount = (riskDist.LOW || 0) + (riskDist.NORMAL || 0);
  const mediumCount = riskDist.MEDIUM || 0;
  const highCount = riskDist.HIGH || 0;
  const criticalCount = riskDist.CRITICAL || 0;

  const riskDistData = [
    { band: 'LOW', count: lowCount, color: '#10b981' },
    { band: 'MEDIUM', count: mediumCount, color: '#f59e0b' },
    { band: 'HIGH', count: highCount, color: '#ea580c' },
    { band: 'CRITICAL', count: criticalCount, color: '#dc2626' },
  ];

  // 3. Events Over Time (Chronological progression from CSV)
  const timelineData = analysis.timeline || [];

  return (
    <div className="analytics-charts-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Row: 2 Key Visual Charts */}
      <div className="charts-grid">
        {/* Chart 1: Successful vs Failed */}
        <motion.div
          role="button"
          tabIndex={0}
          aria-expanded={expandedChart === 'outcome'}
          onClick={() => setExpandedChart(expandedChart === 'outcome' ? null : 'outcome')}
          className={`chart-card ios-expandable-card ${expandedChart === 'outcome' ? 'is-expanded' : ''}`}
          style={{ cursor: 'pointer' }}
          title={`Click to ${expandedChart === 'outcome' ? 'collapse' : 'expand'} chart breakdown`}
          transition={springs.soft}
        >
          <div className="chart-header">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <div className="chart-title">Successful vs. Failed Events</div>
              {expandedChart === 'outcome' && (
                <button
                  type="button"
                  className="ios-collapse-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedChart(null);
                  }}
                >
                  ✕ Collapse
                </button>
              )}
            </div>
          </div>
          <div
            className="chart-body outcome-chart-body"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}
          >
            <div style={{ flex: 1, height: '100%', minHeight: '220px' }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={220}>
                <PieChart>
                  <Pie
                    data={outcomeData.length > 0 ? outcomeData : [{ name: 'No Events', value: 1, color: '#e5e7eb' }]}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {outcomeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="outcome-legend-panel" style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '150px' }}>
              <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: '#ecfdf5', border: '1px solid #a7f3d0' }}>
                <div style={{ fontSize: '11px', color: '#065f46', fontWeight: 600, textTransform: 'uppercase' }}>Successful</div>
                <div style={{ fontSize: '20px', fontWeight: 800, color: '#047857' }}>
                  {successCount.toLocaleString()} <span style={{ fontSize: '13px', fontWeight: 600 }}>({successPct}%)</span>
                </div>
              </div>

              <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: '#fee2e2', border: '1px solid #fecaca' }}>
                <div style={{ fontSize: '11px', color: '#991b1b', fontWeight: 600, textTransform: 'uppercase' }}>Failed</div>
                <div style={{ fontSize: '20px', fontWeight: 800, color: '#b91c1c' }}>
                  {failureCount.toLocaleString()} <span style={{ fontSize: '13px', fontWeight: 600 }}>({failurePct}%)</span>
                </div>
              </div>
            </div>
          </div>

          <AnimatePresence>
            {expandedChart === 'outcome' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={springs.soft}
                className="ios-expand-detail-panel"
                style={{ marginTop: '14px', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="ios-meta-grid">
                  <div className="ios-meta-item">
                    <span className="ios-meta-label">Total Logged</span>
                    <span className="ios-meta-value">{totalEvents.toLocaleString()} authentications</span>
                  </div>
                  <div className="ios-meta-item">
                    <span className="ios-meta-label">Pass Rate</span>
                    <span className="ios-meta-value" style={{ color: '#10b981' }}>{successPct}% Authorized</span>
                  </div>
                  <div className="ios-meta-item">
                    <span className="ios-meta-label">Failure Spike Potential</span>
                    <span className="ios-meta-value" style={{ color: failurePct > 10 ? '#ef4444' : 'inherit' }}>
                      {failurePct > 10 ? 'High Risk' : 'Normal Range'}
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Chart 2: Risk Level Distribution */}
        <motion.div
          role="button"
          tabIndex={0}
          aria-expanded={expandedChart === 'risk'}
          onClick={() => setExpandedChart(expandedChart === 'risk' ? null : 'risk')}
          className={`chart-card ios-expandable-card ${expandedChart === 'risk' ? 'is-expanded' : ''}`}
          style={{ cursor: 'pointer' }}
          title={`Click to ${expandedChart === 'risk' ? 'collapse' : 'expand'} risk band details`}
          transition={springs.soft}
        >
          <div className="chart-header">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <div className="chart-title">Risk Level Distribution</div>
              {expandedChart === 'risk' && (
                <button
                  type="button"
                  className="ios-collapse-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedChart(null);
                  }}
                >
                  ✕ Collapse
                </button>
              )}
            </div>
          </div>
          <div className="chart-body" style={{ minHeight: '220px' }}>
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={220}>
              <BarChart data={riskDistData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="band" tick={{ fontSize: 11, fontWeight: 600 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} name="Events Count">
                  {riskDistData.map((entry) => (
                    <Cell key={entry.band} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <AnimatePresence>
            {expandedChart === 'risk' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={springs.soft}
                className="ios-expand-detail-panel"
                style={{ marginTop: '14px', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="ios-meta-grid">
                  <div className="ios-meta-item">
                    <span className="ios-meta-label">Low Risk Safe</span>
                    <span className="ios-meta-value" style={{ color: '#10b981' }}>{lowCount} events</span>
                  </div>
                  <div className="ios-meta-item">
                    <span className="ios-meta-label">Medium Anomaly</span>
                    <span className="ios-meta-value" style={{ color: '#f59e0b' }}>{mediumCount} events</span>
                  </div>
                  <div className="ios-meta-item">
                    <span className="ios-meta-label">High / Critical Threat</span>
                    <span className="ios-meta-value" style={{ color: '#dc2626' }}>{highCount + criticalCount} events</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Full-width Row: Events Over Time */}
      <motion.div
        role="button"
        tabIndex={0}
        aria-expanded={expandedChart === 'timeline'}
        onClick={() => setExpandedChart(expandedChart === 'timeline' ? null : 'timeline')}
        className={`chart-card ios-expandable-card ${expandedChart === 'timeline' ? 'is-expanded' : ''}`}
        style={{ width: '100%', cursor: 'pointer' }}
        title={`Click to ${expandedChart === 'timeline' ? 'collapse' : 'expand'} temporal details`}
        transition={springs.soft}
      >
        <div className="chart-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <div className="chart-title">Events Over Time</div>
            {expandedChart === 'timeline' && (
              <button
                type="button"
                className="ios-collapse-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedChart(null);
                }}
              >
                ✕ Collapse
              </button>
            )}
          </div>
        </div>
        <div className="chart-body" style={{ height: '260px', minHeight: '260px' }}>
          {timelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={260}>
              <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0066ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0066ff" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorFailures" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="events"
                  stroke="#0066ff"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorEvents)"
                  name="Total Events"
                />
                <Area
                  type="monotone"
                  dataKey="failures"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorFailures)"
                  name="Failures"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--text-tertiary)',
                fontSize: '13px',
              }}
            >
              Single timestamp snapshot recorded in uploaded dataset
            </div>
          )}
        </div>

        <AnimatePresence>
          {expandedChart === 'timeline' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={springs.soft}
              className="ios-expand-detail-panel"
              style={{ marginTop: '14px', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="ios-meta-grid">
                <div className="ios-meta-item">
                  <span className="ios-meta-label">Time Slices</span>
                  <span className="ios-meta-value">{timelineData.length} observation buckets</span>
                </div>
                <div className="ios-meta-item">
                  <span className="ios-meta-label">Temporal Density</span>
                  <span className="ios-meta-value">Continuous Hourly Telemetry</span>
                </div>
                <div className="ios-meta-item">
                  <span className="ios-meta-label">Interpolation</span>
                  <span className="ios-meta-value">Monotone Bezier Spline</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
