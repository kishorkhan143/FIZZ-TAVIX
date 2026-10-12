/**
 * RiskChart: Time-series visualization of risk score over time.
 * Uses recharts for real-time updates.
 */

import React from 'react';
import { motion } from 'motion/react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';
import { parseUtc } from '../useAuthSentinel';

// AnimatedTooltip MUST be a stable named component at module level.
// Defining it inside render (or useCallback) causes Recharts to see a new
// component type on every render, which remounts the tooltip and causes flicker.
function AnimatedTooltip({ active, payload, label }) {
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = parseUtc(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  if (!active || !payload?.length) return null;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96, y: -4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.14, ease: [0.22, 1, 0.36, 1] }}
      style={{
        backgroundColor: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: '0.5rem',
        padding: '8px 12px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
        fontSize: '13px',
        pointerEvents: 'none',
      }}
    >
      <p style={{ margin: 0, color: '#6b7280', marginBottom: 4 }}>{formatTime(label)}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ margin: '2px 0', fontWeight: 600, color: entry.color }}>
          {typeof entry.value === 'number' ? `${entry.value.toFixed(1)}` : entry.value}
        </p>
      ))}
    </motion.div>
  );
}

export default function RiskChart({ 
  data = [],
  height = 300,
  showThresholds = true,
  animated = true 
}) {
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = parseUtc(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  // Memoize data so the chart doesn't re-animate on unrelated parent renders
  const chartData = React.useMemo(() => data, [data]);

  if (!data || data.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15 }}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: `${height}px`,
          backgroundColor: '#f9fafb',
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb',
          color: '#9ca3af'
        }}
      >
        No data available
      </motion.div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart 
        data={chartData}
        margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
      >
        <defs>
          <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTime}
          tick={{ fontSize: 12 }}
        />
        
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12 }}
          label={{ value: 'Risk Score', angle: -90, position: 'insideLeft' }}
        />
        
        <Tooltip
          content={<AnimatedTooltip />}
        />
        
        {showThresholds && (
          <>
            {/* Incident threshold (60) */}
            <ReferenceLine
              y={60}
              stroke="#f59e0b"
              strokeDasharray="5 5"
              label={{ 
                value: 'Incident (60)', 
                position: 'right', 
                fill: '#f59e0b', 
                fontSize: 11 
              }}
            />
            
            {/* Cool threshold (30) */}
            <ReferenceLine
              y={30}
              stroke="#10b981"
              strokeDasharray="5 5"
              label={{ 
                value: 'Cool (30)', 
                position: 'right', 
                fill: '#10b981', 
                fontSize: 11 
              }}
            />
          </>
        )}
        
        <Area
          type="monotone"
          dataKey="score"
          stroke="#3b82f6"
          fillOpacity={1}
          fill="url(#colorScore)"
          isAnimationActive={animated}
          animationDuration={900}
          animationEasing="ease-out"
          dot={false}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
