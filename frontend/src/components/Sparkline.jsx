import React from 'react';
import { motion } from 'motion/react';

/**
 * Sparkline component for statistic cards.
 * Renders a clean, smooth SVG trend curve with subtle area shading.
 * Fully responsive without external chart library layout delays or dot artifacts.
 */
export default function Sparkline({
  data = [],
  color = '#0066ff',
  height = 40,
  id = 'sparkline',
}) {
  const width = 100;
  const paddingTop = 4;
  const paddingBottom = 4;
  const innerHeight = height - paddingTop - paddingBottom;

  const validData = Array.isArray(data) && data.length > 0 ? data : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
  const max = Math.max(...validData, 0);
  const range = max > 0 ? max : 1;

  // Calculate points on SVG grid (0..100 width, 0..height height)
  const points = validData.map((val, idx) => {
    const x = Number(((idx / (validData.length - 1)) * width).toFixed(2));
    const y = max === 0
      ? height - paddingBottom - 2
      : Number((height - paddingBottom - (val / range) * innerHeight).toFixed(2));
    return { x, y };
  });

  // Smooth bezier curve (Monotone cubic spline between segments)
  let lineD = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const midX = Number(((p0.x + p1.x) / 2).toFixed(2));
    lineD += ` C ${midX} ${p0.y}, ${midX} ${p1.y}, ${p1.x} ${p1.y}`;
  }

  // Closed area path for gradient shading
  const areaD = `${lineD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;
  const gradId = `sparkline-grad-${id}`;

  return (
    <motion.div
      className="sparkline-container"
      initial={{ opacity: 0, scaleY: 0.85 }}
      animate={{ opacity: 1, scaleY: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      style={{
        width: '100%',
        height: `${height}px`,
        overflow: 'hidden',
        pointerEvents: 'none',
        transformOrigin: 'bottom center',
      }}
    >
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        style={{ width: '100%', height: '100%', display: 'block' }}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="75%" stopColor={color} stopOpacity="0.05" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>
        <path d={areaD} fill={`url(#${gradId})`} />
        <path
          d={lineD}
          fill="none"
          stroke={color}
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </motion.div>
  );
}

/**
 * Computes trend interval buckets from real authentication events and alerts.
 * Groups records into N uniform time intervals spanning the observed timeframe.
 */
export function generateTrendIntervals(events = [], alerts = [], numIntervals = 12) {
  const parseTime = (ts) => {
    if (!ts) return null;
    const s = String(ts);
    const d = new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(s) ? s : s + 'Z');
    return isNaN(d.getTime()) ? null : d.getTime();
  };

  const eventTimes = (events || []).map((e) => parseTime(e.timestamp)).filter(Boolean);
  const alertTimes = (alerts || []).map((a) => parseTime(a.triggered_at)).filter(Boolean);
  const allTimes = [...eventTimes, ...alertTimes];

  if (allTimes.length === 0) {
    const zeros = Array(numIntervals).fill(0);
    return {
      total: zeros,
      successful: zeros,
      failed: zeros,
      alerts: zeros,
    };
  }

  let minT = Math.min(...allTimes);
  let maxT = Math.max(...allTimes);

  // If time window is tight, expand with modest buffer so intervals distribute smoothly
  if (maxT - minT < 60000) {
    minT -= 30000;
    maxT += 30000;
  }

  const duration = maxT - minT;
  const intervalSize = duration / numIntervals;

  const total = Array(numIntervals).fill(0);
  const successful = Array(numIntervals).fill(0);
  const failed = Array(numIntervals).fill(0);
  const alertCounts = Array(numIntervals).fill(0);

  (events || []).forEach((e) => {
    const t = parseTime(e.timestamp);
    if (!t) return;
    let idx = Math.floor((t - minT) / intervalSize);
    if (idx < 0) idx = 0;
    if (idx >= numIntervals) idx = numIntervals - 1;
    total[idx] += 1;
    if (e.status === 'SUCCESS') {
      successful[idx] += 1;
    } else if (e.status === 'FAILURE') {
      failed[idx] += 1;
    }
  });

  (alerts || []).forEach((a) => {
    const t = parseTime(a.triggered_at);
    if (!t) return;
    let idx = Math.floor((t - minT) / intervalSize);
    if (idx < 0) idx = 0;
    if (idx >= numIntervals) idx = numIntervals - 1;
    alertCounts[idx] += 1;
  });

  return {
    total,
    successful,
    failed,
    alerts: alertCounts,
  };
}
