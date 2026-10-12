/**
 * RiskGauge: Display 0-100 risk score with color-coded bands.
 * NORMAL (0-29) green | WATCH (30-59) amber | SUSPICIOUS (60-79) orange | HIGH_RISK (80-100) red
 */

import React from 'react';
import { motion, useMotionValue, animate } from 'motion/react';
import { springs, calculateDashOffset } from '../motion';
import './RiskGauge.css';

export default function RiskGauge({ 
  score = 0, 
  size = 'medium',
  showLabel = true,
  onClick = null 
}) {
  const getRiskBand = (s) => {
    if (s >= 80) return 'HIGH_RISK';
    if (s >= 60) return 'SUSPICIOUS';
    if (s >= 30) return 'WATCH';
    return 'NORMAL';
  };

  const getBandColor = (band) => {
    const colors = {
      NORMAL: '#10b981',      // Green
      WATCH: '#f59e0b',       // Amber
      SUSPICIOUS: '#f97316',  // Orange
      HIGH_RISK: '#ef4444'    // Red
    };
    return colors[band] || '#6b7280';  // Gray default
  };

  const band = getRiskBand(score);
  const color = getBandColor(band);
  
  // Percentage for arc (0-100%)
  const percentage = Math.min(100, Math.max(0, score));
  // Circumference of circle with radius 45
  const circumference = 2 * Math.PI * 45;
  
  // Motion values for animation
  const dashOffsetMV = useMotionValue(calculateDashOffset(score, circumference));
  const [displayScore, setDisplayScore] = React.useState(Math.round(score));
  const prevScoreRef = React.useRef(score);

  React.useEffect(() => {
    const from = prevScoreRef.current;
    const to = score;
    prevScoreRef.current = to;
    
    // Animate arc
    animate(dashOffsetMV, calculateDashOffset(to, circumference), springs.soft);
    
    // Animate displayed number
    animate(from, to, {
      ...springs.soft,
      onUpdate: (v) => setDisplayScore(Math.round(v)),
    });
  }, [score, circumference, dashOffsetMV]);

  return (
    <motion.div 
      className={`risk-gauge risk-gauge-${size}`}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      whileHover={{ y: -2 }}
      transition={springs.soft}
    >
      <svg viewBox="0 0 100 100" className="gauge-svg">
        {/* Background circle */}
        <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="2" />
        
        {/* Colored progress arc */}
        <motion.circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffsetMV}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          animate={{ stroke: color }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        />
        
        {/* Center score text */}
        <text 
          x="50" 
          y="45" 
          textAnchor="middle" 
          className="gauge-text"
          style={{ fill: color }}
        >
          {displayScore}
        </text>
        
        {/* Band label in center */}
        <text 
          x="50" 
          y="60" 
          textAnchor="middle" 
          className="gauge-band-text"
          style={{ fontSize: '10px', fill: '#6b7280' }}
        >
          {band}
        </text>
      </svg>
      
      {showLabel && (
        <div className="gauge-label" style={{ color }}>
          {band}
        </div>
      )}
    </motion.div>
  );
}
